import streamlit as st
from core.search_engine import SearchEngine

# הגדרות עמוד - חייב להיות השורה הראשונה של Streamlit
st.set_page_config(page_title="Japanika Smart Waiter", page_icon="🍣", layout="wide")

# שימוש בסינגלטון - הטעינה תתבצע רק פעם אחת
@st.cache_resource
def init_engine():
    engine = SearchEngine()
    # בדיקה אם צריך להזריק נתונים (רק אם ה-DB ריק)
    if engine.collection.count() == 0:
        with st.spinner("טוען תפריט מועשר של ג'פניקה..."):
            # כאן עדכנתי את השם לקובץ הנכון שלך
            engine.ingest_data("japanika_menu_enriched_complete.csv") 
    return engine

search_ai = init_engine()

# עיצוב בסיסי בעזרת CSS להצמדה לימין (RTL)
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stExpander { background-color: #f9f9f9; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# כותרת האפליקציה
st.title("🍣 עוזר המלצרים של ג'פניקה")
st.subheader("חיפוש מנות חכם מבוסס AI")

# תפריט צדדי (Sidebar) לפילטרים מהירים
with st.sidebar:
    st.image("https://www.japanika.net/wp-content/themes/japanika/images/logo.png", width=150)
    st.header("פילטרים")
    category = st.selectbox("קטגוריה", 
                            [None, "מנות פתיחה", "סושי", "עיקריות", "קינוחים", "משקאות"])
    
    st.divider()
    st.info("טיפ: אפשר לחפש משפטים כמו 'משהו חריף עם טונה' או 'קינוח ללא גלוטן'")

# שורת החיפוש המרכזית
query = st.text_input("מה הלקוח מחפש?", placeholder="למשל: סושי עם בטטה וקראנץ'...")

if query:
    # ביצוע החיפוש דרך המנוע שבנינו
    results = search_ai.search(query, n_results=5, category_filter=category)
    
    if results and results['documents']:
        st.write(f"נמצאו {len(results['documents'][0])} מנות מתאימות:")
        
        # הצגת התוצאות בפורמט של כרטיסים
        for i in range(len(results['documents'][0])):
            metadata = results['metadatas'][0][i]
            doc = results['documents'][0][i]
            
            # יצירת כותרת הכרטיס
            card_title = f"{metadata['name']} | 💰 {metadata['price']} ₪"
            
            with st.expander(card_title):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**תיאור:** {doc}")
                    st.write(f"**קטגוריה:** {metadata['category']}")
                
                with col2:
                    # הצגת אייקונים לפי מאפייני המנה
                    if str(metadata.get('is_vegan')) == 'True':
                        st.success("🌿 טבעוני")
                    if str(metadata.get('is_gf')) == 'True':
                        st.warning("🌾 ללא גלוטן")
    else:
        st.warning("לא נמצאו מנות תואמות. נסה תיאור אחר.")

else:
    # הודעה שמופיעה כשאין חיפוש
    st.info("הקלד תיאור מנה כדי להתחיל בחיפוש.")