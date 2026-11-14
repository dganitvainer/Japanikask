import streamlit as st
from core.search_engine import SearchEngine 

st.set_page_config(page_title="Japanika Smart Waiter", page_icon="🍣", layout="wide")

@st.cache_resource
def init_engine():
    engine = SearchEngine()
    with st.spinner("טוען תפריט מועשר של ג'פניקה..."):
        engine.ensure_index("japanika_menu_enriched_complete.csv")
    return engine

search_ai = init_engine()

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[role="radiogroup"] { direction: rtl; }
    label[data-testid="stWidgetLabel"] { text-align: right; width: 100%; }
    .stExpander { background-color: #f9f9f9; border-radius: 10px; text-align: right; }
    input { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("🍣 עוזר המלצרים של ג'פניקה")
st.subheader("חיפוש מנות חכם מבוסס AI")

with st.sidebar:
    st.image("https://www.japanika.net/wp-content/themes/japanika/images/logo.png", width=150)
    st.header("פילטרים והעדפות")
    
    # Key names match the CSV columns (is_vegetarian, kid_friendly)
    filters_config = {
        'is_vegan': '🌱 טבעוני',
        'is_vegetarian': '🥗 צמחוני', # fixed key name
        'is_spicy': '🌶️ חריף',
        'contains_gluten': '🍞 גלוטן',
        'contains_dairy': '🥛 חלבי',
        'raw_fish': '🐟 דג נא',
        'is_fried': '🍤 מטוגן',
        'kid_friendly': '👶 מתאים לילדים' # fixed key name
    }
    
    active_buttons = {}
    for col_id, label in filters_config.items():
        choice = st.radio(label, ["הכל", "עם", "ללא"], index=0, key=col_id, horizontal=True)
        if choice == "עם":
            active_buttons[col_id] = True
        elif choice == "ללא":
            active_buttons[col_id] = False

    st.divider()
    st.info("טיפ: לחיצה על Enter בשורת החיפוש תפעיל את המנוע אוטומטית.")

with st.form("search_form"):
    query = st.text_input("מה הלקוח מחפש?", placeholder="למשל: סושי עם בטטה וקראנץ'...")
    submit_button = st.form_submit_button("חיפוש מנה", type="primary")

if submit_button and (query or active_buttons):
    results = search_ai.search(query, active_buttons=active_buttons)["results"]

    if results:
        st.write(f"נמצאו {len(results)} מנות מתאימות:")

        for metadata in results:
            relevance = metadata.get('relevance')
            
            # --- metadata keys match the CSV column names ---
            dish_name = metadata.get('dish_name', 'ללא שם') # full key name
            price = metadata.get('price', 'לא צוין')
            category = metadata.get('category', 'כללי')
            description = metadata.get('original_description', 'אין תיאור זמין') # full key name
            flavor_profile = metadata.get('flavor_profile', 'לא צוין') # added flavor profile
            
            card_title = f"{dish_name} | 💰 {price} | 🏷️ {category}"
            
            with st.expander(card_title):
                st.write(f"**תיאור מורחב:** {description}")
                st.write(f"**פרופיל טעמים:** {flavor_profile}") # show the flavor profile

                cols = st.columns(4)
                # Flags are normalized to כן / לא / אפשרי (yes / no / maybe)
                if metadata.get('is_vegan') != 'לא': 
                    cols[0].success("🌱 טבעוני")
                if metadata.get('contains_gluten') == 'לא': 
                    cols[1].warning("🍞 ללא גלוטן")
                if metadata.get('is_spicy') != 'לא': 
                    cols[2].error("🌶️ חריף")
                
                if relevance is not None:
                    st.caption(f"רמת רלוונטיות: {relevance:.2%}")
    else:
        st.warning("לא נמצאו מנות תואמות לשילוב הנבחר. נסה לשנות את הפילטרים או את התיאור.")
elif not query:
    st.info("הקלד תיאור מנה או בחר פילטר כדי להתחיל.")