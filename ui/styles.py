import streamlit as st

def apply_styles():
    """Apply custom CSS styles to the app."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600&display=swap');
        
        .stApp {
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        }
        
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 600 !important;
            color: #e0e0e0 !important;
        }
        
        p, span, label, .stMarkdown {
            color: #c0c0c0 !important;
        }
        
        .stCheckbox label span {
            color: #e0e0e0 !important;
        }
        
        .main-title {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 600;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf, #ff006e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            font-family: 'JetBrains Mono', monospace;
            color: #a0a0a0;
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }
        
        .status-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.2rem;
            margin: 1rem 0;
        }
        
        .status-connected {
            border-left: 4px solid #00ff88;
        }
        
        .status-disconnected {
            border-left: 4px solid #ff4757;
        }
        
        .stMultiSelect > div {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        
        .stButton > button {
            font-family: 'Outfit', sans-serif;
            font-weight: 500;
            background: linear-gradient(90deg, #7b2cbf, #00d4ff);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 2rem;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(123, 44, 191, 0.3);
        }
        
        .stDownloadButton > button {
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(90deg, #00ff88, #00d4ff);
            color: #0f0f1a;
            font-weight: 600;
        }
        
        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
            color: #c0c0c0;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, rgba(123, 44, 191, 0.3), rgba(0, 212, 255, 0.3));
            color: #fff !important;
        }
    </style>
    """, unsafe_allow_html=True)

