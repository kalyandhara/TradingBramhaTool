#!/usr/bin/env python3
"""Telegram Signals — extracted from the monolith (B-87r, second page).

Moved VERBATIM: the body below is the `if current_page == "Telegram Signals":`
block as it stood, dedented one level and wrapped in `render()`. Nothing was
renamed, reordered or improved in the move, for the reason the first extraction
recorded — a move and an edit in one commit is a move you cannot verify.

Its one coupling to `dashboard_app` was `_paginated_df`, which is why
`ui_tables` was lifted out first. Everything else it needs it imports for
itself.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

import telegram_signals as tg
import ui_tables as uit


def render() -> None:
    st.subheader("Telegram Trading Signals")
    st.caption(
        "Track trading signals from Telegram channels (Rohan Das RPCI, TechnoFunda, etc). "
        "Manually add signals, track entries/exits, and measure performance."
    )

    # Initialize signal manager
    ts = tg.TelegramSignals()

    # Tab sections
    signal_tab1, signal_tab_fetch, signal_tab2, signal_tab3, signal_tab4 = st.tabs(
        ["Add Signal", "Fetch from Channel", "Active Signals", "Signal History", "Statistics"]
    )

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Fetch from public Telegram preview
    with signal_tab_fetch:
        st.subheader("Fetch from Public Telegram Preview")
        st.caption(
            "Pulls the ~20 most recent posts from `t.me/s/<channel>` (no auth). "
            "Preview truncates long posts — verify on Telegram before saving."
        )
        fetch_col1, fetch_col2 = st.columns([3, 1])
        with fetch_col1:
            fetch_channel_name = st.text_input(
                "Channel username (without @)",
                value="FinanceWithSunil",
                key="fetch_tg_channel",
            )
        with fetch_col2:
            st.write("")
            st.write("")
            do_fetch = st.button("Fetch posts", type="primary", key="fetch_tg_btn")

        if do_fetch:
            try:
                import telegram_preview_scraper as tps
                with st.spinner(f"Fetching @{fetch_channel_name}..."):
                    posts = tps.fetch_channel(fetch_channel_name)
                st.session_state["tg_fetched_posts"] = [p.to_dict() for p in posts]
                st.session_state["tg_fetched_channel"] = fetch_channel_name
                st.success(f"Fetched {len(posts)} posts.")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

        posts_cache = st.session_state.get("tg_fetched_posts", [])
        if posts_cache:
            channel_label = f"@{st.session_state.get('tg_fetched_channel', fetch_channel_name)}"
            st.markdown(f"**{len(posts_cache)} posts from {channel_label}** (newest last)")
            for idx, p in enumerate(posts_cache):
                header = f"[{p.get('posted_at', '?')}] {' · '.join(p.get('tickers') or []) or '(no ticker detected)'}"
                with st.expander(header, expanded=False):
                    st.write(p.get("text", ""))
                    if p.get("url"):
                        st.markdown(f"[Open on Telegram]({p['url']})")
                    tickers = p.get("tickers") or []
                    if tickers:
                        pick = st.selectbox(
                            "Symbol to save",
                            tickers,
                            key=f"tg_pick_{idx}",
                        )
                        if st.button("Save as PENDING signal", key=f"tg_save_{idx}"):
                            try:
                                posted = None
                                if p.get("posted_at"):
                                    posted = datetime.fromisoformat(
                                        p["posted_at"].replace("Z", "+00:00")
                                    ).date()
                            except Exception:
                                posted = date.today()
                            sig = ts.add_signal_from_dict({
                                "symbol": pick,
                                "channel": channel_label,
                                "posted_date": posted or date.today(),
                                "strategy": "",
                                "signal_source": "OTHER",
                                "timeframe": "",
                                "confidence": 5,
                                "notes": (p.get("text") or "") + (f"\n\nSource: {p['url']}" if p.get("url") else ""),
                                "metadata": {"source_url": p.get("url"), "posted_at": p.get("posted_at")},
                            })
                            st.success(f"Saved {sig.signal_id}")

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Add New Signal
    with signal_tab1:
        st.subheader("Add Signal from Telegram")

        col1, col2 = st.columns(2)

        with col1:
            channel = st.text_input(
                "Telegram Channel",
                value="Rohan Das (@rohaninvestor)",
                placeholder="e.g., Rohan Das (@rohaninvestor)"
            )
            symbol = st.text_input(
                "Stock Symbol",
                value="",
                placeholder="e.g., MOTHERSON, RELIANCE, TCS"
            ).upper()
            signal_date = st.date_input("Signal Posted Date", value=date.today())
            strategy = st.text_input(
                "Strategy/Indicator",
                value="RPCI",
                placeholder="e.g., RPCI, TechnoFunda, Chart Pattern"
            )

        with col2:
            timeframe = st.selectbox(
                "Timeframe",
                ["Intraday", "Short-term (1-3 days)", "Medium-term (1-4 weeks)", "Long-term (1-3 months)"]
            )
            confidence = st.slider("Confidence Level", min_value=1, max_value=10, value=5)
            entry_price = st.number_input("Entry Price (Optional)", value=0.0, step=0.01)
            target_price = st.number_input("Target Price (Optional)", value=0.0, step=0.01)
            stop_loss = st.number_input("Stop Loss (Optional)", value=0.0, step=0.01)

        notes = st.text_area(
            "Notes/Analysis",
            height=150,
            placeholder="Paste signal details, analysis, or key points from Telegram post..."
        )

        # Pre-filled Rohan Das RPCI example
        if st.button("Load Example: Rohan Das RPCI (MOTHERSON)", key='example_rpci'):
            symbol = 'MOTHERSON'
            strategy = 'RPCI Indicator'
            channel = 'Rohan Das (@rohaninvestor)'
            signal_date = date(2026, 6, 25)
            confidence = 8
            timeframe = 'Medium-term (1-4 weeks)'
            notes = (
                "RPCI identified MOTHERSON before SEBI RA recommendation.\n"
                "Stock recommended for next week accumulation.\n"
                "RPCI simplifies technical analysis with rule-based signals.\n"
                "Used by 1500+ traders including SEBI registered users.\n\n"
                "SEBI RA confirmation: 27 June for next week accumulation."
            )

            st.session_state.signal_symbol = symbol
            st.session_state.signal_channel = channel
            st.session_state.signal_strategy = strategy
            st.session_state.signal_date = signal_date
            st.session_state.signal_confidence = confidence
            st.session_state.signal_timeframe = timeframe
            st.session_state.signal_notes = notes
            st.rerun()

        if st.button("Add Signal", type="primary", key='add_signal_btn'):
            if not symbol or not channel:
                st.error("Symbol and Channel are required")
            else:
                signal_data = {
                    'symbol': symbol,
                    'channel': channel,
                    'posted_date': signal_date,
                    'strategy': strategy,
                    'signal_source': strategy.upper().replace(' ', '_') if strategy else 'OTHER',
                    'timeframe': timeframe,
                    'confidence': confidence,
                    'entry_price': entry_price if entry_price > 0 else None,
                    'target_price': target_price if target_price > 0 else None,
                    'stop_loss': stop_loss if stop_loss > 0 else None,
                    'notes': notes,
                    'metadata': {
                        'added_on': datetime.now().isoformat(),
                        'manual_entry': True,
                    }
                }

                signal = ts.add_signal_from_dict(signal_data)
                st.success(f"Signal added: {signal.signal_id}")
                st.balloons()

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Active Signals
    with signal_tab2:
        st.subheader("Active & Pending Signals")

        active = ts.get_active_signals()

        if not active:
            st.info("No active signals. Add one above.")
        else:
            for signal in active:
                with st.expander(f"{signal.symbol} — {signal.strategy} (Confidence: {signal.confidence}/10)", expanded=False):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Symbol", signal.symbol)
                        st.metric("Channel", signal.channel[:30])
                        st.metric("Status", signal.status.value.title())

                    with col2:
                        st.metric("Entry Price", f"₹{signal.entry_price}" if signal.entry_price else "—")
                        st.metric("Target", f"₹{signal.target_price}" if signal.target_price else "—")
                        st.metric("Stop Loss", f"₹{signal.stop_loss}" if signal.stop_loss else "—")

                    with col3:
                        st.metric("Timeframe", signal.timeframe or "—")
                        st.metric("Confidence", f"{signal.confidence}/10")
                        st.metric("Posted", signal.posted_date.strftime('%d-%b') if signal.posted_date else "—")

                    if signal.notes:
                        st.write("**Notes:**")
                        st.caption(signal.notes)

                    # Update signal status
                    col_update1, col_update2, col_update3, col_update4 = st.columns(4)
                    with col_update1:
                        if st.button("Mark Active", key=f"active_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.ACTIVE, entry_date=date.today())
                            st.rerun()
                    with col_update2:
                        if st.button("Partial Exit", key=f"partial_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.PARTIAL)
                            st.rerun()
                    with col_update3:
                        exit_return = st.number_input("Return %", value=0.0, step=0.1, key=f"return_{signal.signal_id}")
                        if st.button("Close", key=f"close_{signal.signal_id}"):
                            ts.update_signal(
                                signal.signal_id,
                                status=tg.SignalStatus.CLOSED,
                                exit_date=date.today(),
                                realized_return=exit_return
                            )
                            st.rerun()
                    with col_update4:
                        if st.button("Cancel", key=f"cancel_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.CANCELLED)
                            st.rerun()

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Signal History
    with signal_tab3:
        st.subheader("All Signals History")

        if not ts.signals:
            st.info("No signals recorded yet.")
        else:
            # Display as table
            signal_list = []
            for sig_id, signal in ts.signals.items():
                signal_list.append({
                    'Symbol': signal.symbol,
                    'Channel': signal.channel[:20],
                    'Strategy': signal.strategy,
                    'Status': signal.status.value.title(),
                    'Confidence': f"{signal.confidence}/10",
                    'Entry': f"₹{signal.entry_price}" if signal.entry_price else "—",
                    'Target': f"₹{signal.target_price}" if signal.target_price else "—",
                    'Return %': f"{signal.realized_return}%" if signal.realized_return else "—",
                    'Posted': signal.posted_date.strftime('%d-%b-%y') if signal.posted_date else "—",
                })

            df_signals = pd.DataFrame(signal_list)
            uit.paginated_df(df_signals, key="telegram_signals")

            # Export option
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv_export = ts.export_to_csv()
                if csv_export:
                    st.success(f"Exported to: `{csv_export}`")

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Statistics
    with signal_tab4:
        st.subheader("Signal Performance Statistics")

        stats = ts.get_signal_statistics()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Signals", stats['total_signals'])
        with col2:
            st.metric("Active/Pending", stats['active_signals'])
        with col3:
            st.metric("Closed", stats['closed_signals'])
        with col4:
            st.metric("Win Rate", f"{stats['win_rate']}%" if stats['closed_signals'] > 0 else "—")

        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("Avg Return", f"{stats['avg_return']}%" if stats['closed_signals'] > 0 else "—")
        with col6:
            st.metric("Total Return", f"{stats['total_return']}%" if stats['closed_signals'] > 0 else "—")
        with col7:
            st.metric("Best Signal", stats['best_return'] if stats['best_signal'] else "—")

        # By channel breakdown
        st.subheader("Signals by Channel")
        channels = {}
        for signal in ts.signals.values():
            if signal.channel not in channels:
                channels[signal.channel] = 0
            channels[signal.channel] += 1

        if channels:
            channel_df = pd.DataFrame(
                list(channels.items()),
                columns=['Channel', 'Signal Count']
            ).sort_values('Signal Count', ascending=False)
            st.dataframe(channel_df, width="stretch", hide_index=True)

        # By strategy breakdown
        st.subheader("Signals by Strategy")
        strategies = {}
        for signal in ts.signals.values():
            if signal.strategy not in strategies:
                strategies[signal.strategy] = 0
            strategies[signal.strategy] += 1

        if strategies:
            strategy_df = pd.DataFrame(
                list(strategies.items()),
                columns=['Strategy', 'Signal Count']
            ).sort_values('Signal Count', ascending=False)
            st.dataframe(strategy_df, width="stretch", hide_index=True)
