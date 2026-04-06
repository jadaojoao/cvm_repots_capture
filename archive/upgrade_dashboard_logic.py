# -*- coding: utf-8 -*-
import os
import time

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\dashboard\update_center.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _progress_callback with calculated Velocity and Custom HTML
new_callback = """        start_time = time.time()

        def _progress_callback(done_count, total_count, current_company, success_count, error_count):
            now = time.time()
            elapsed = now - start_time
            # Velocity: companies per minute
            velocity = (done_count / (elapsed / 60)) if elapsed > 5 else 0
            
            pct = int((done_count / total_count) * 100) if total_count else 100
            
            # Premium Velocity UI with Shimmer Bar
            progress_bar.markdown(f'''
                <div class="velocity-container">
                    <div class="velocity-stats">
                        <span class="velocity-label">Progress: {done_count}/{total_count}</span>
                        <span class="velocity-value">{velocity:.1f} <small style="font-size:0.6rem; color:var(--text-muted)">COMP/MIN</small></span>
                    </div>
                    <div class="velocity-bar-bg">
                        <div class="velocity-bar-fill" style="width: {pct}%"></div>
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 4px;">
                        Processing <span class="pulse-active" style="color: var(--accent); font-weight: 600;">{current_company}</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            counters.caption(
                f"⏱️ Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s • "
                f"✅ Success: {success_count} • ❌ Error: {error_count}"
            )"""

# Find the old _progress_callback block and replace it
old_callback_start = content.find('        def _progress_callback(done_count, total_count, current_company, success_count, error_count):')
old_callback_end = content.find('            )', old_callback_start) + 14 # End of counters.caption

if old_callback_start != -1:
    print("Found old progress callback, upgrading to Velocity UI...")
    # Also need to import time
    if 'import time' not in content:
        content = content.replace('import sys', 'import sys\nimport time')
    
    # Replace the block
    # We need to find the line starting with progress_bar = st.progress(0)
    pb_start = content.rfind('progress_bar = st.progress(0)', 0, old_callback_start)
    if pb_start != -1:
        # Replace from progress_bar = st.progress(0) to end of counters.caption
        content = content[:pb_start] + "progress_bar = st.empty()\n" + new_callback + content[old_callback_end:]

# 2. Cleanup: remove standard st.progress(100) at the end
content = content.replace('        progress_bar.progress(100)', '        # progress_bar.progress(100)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimization UI Logic: Update Center upgraded with Velocity metrics and Shimmer UI.")
