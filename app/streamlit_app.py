from __future__ import annotations

import streamlit as st


# Explicit navigation prevents Streamlit from turning every legacy file in
# app/pages into a top-level menu item. The product has one main interface
# and one data bridge, not a page graveyard.

pages = [
    st.Page("pages/00_Iskra_Forge.py", title="Iskra Forge", icon="*", default=True),
    st.Page("pages/01_Supabase_Bridge.py", title="Data Bridge", icon="DB"),
]

st.navigation(pages).run()
