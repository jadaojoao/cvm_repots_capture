# -*- coding: utf-8 -*-
import os

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\dashboard\styles\style.css'
with open(path, 'a', encoding='utf-8') as f:
    f.write("\n\n/* ── Velocity & Performance UI ────────────────────────────────── */\n")
    f.write("@keyframes shimmer {\n    0% { background-position: -200% 0; }\n    100% { background-position: 200% 0; }\n}\n\n")
    f.write(".velocity-container {\n    background: var(--bg-card);\n    border: 1px solid var(--border);\n    border-radius: var(--r-md);\n    padding: 16px;\n    margin-bottom: 12px;\n    position: relative;\n    overflow: hidden;\n    animation: fadeInUp 0.4s var(--t-smooth);\n}\n\n")
    f.write(".velocity-bar-bg {\n    height: 8px;\n    background: var(--bg-hover);\n    border-radius: 4px;\n    overflow: hidden;\n    margin: 10px 0;\n}\n\n")
    f.write(".velocity-bar-fill {\n    height: 100%;\n    background: linear-gradient(90deg, var(--accent-dk), var(--accent), var(--accent-lt));\n    background-size: 200% 100%;\n    animation: shimmer 2s infinite linear;\n    border-radius: 4px;\n    transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);\n    box-shadow: 0 0 12px var(--accent-glow-md);\n}\n\n")
    f.write(".velocity-stats {\n    display: flex;\n    justify-content: space-between;\n    align-items: baseline;\n}\n\n")
    f.write(".velocity-value {\n    font-size: 1.2rem;\n    font-weight: 800;\n    color: var(--accent);\n    font-family: var(--font-headline);\n}\n\n")
    f.write(".velocity-label {\n    font-size: 0.65rem;\n    color: var(--text-muted);\n    text-transform: uppercase;\n    letter-spacing: 0.08em;\n    font-weight: 600;\n}\n\n")
    f.write(".pulse-active {\n    animation: pulse-subtle 2s infinite ease-in-out;\n}\n")

print("Optimization UI: CSS animations added to style.css.")
