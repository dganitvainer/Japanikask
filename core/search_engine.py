import chromadb
from chromadb.utils import embedding_functions
import pandas as pd

class SearchEngine:
    _instance = None  # כאן נשמור את המופע היחיד

    def __new__(cls, *args, **kwargs):
        """מבטיח שיווצר רק אובייקט אחד מהמחלקה"""
        if cls._instance is None:
            cls._instance = super(SearchEngine, cls).__new__(cls)
            # סימון שהמופע עוד לא עבר את האתחול של Chroma
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 1. יצירת לקוח ששומר נתונים על הדיסק
            self.client = chromadb.PersistentClient(path="./chroma_db")
            
            # 2. הגדרת פונקציית Embedding (ה"מתרגם" של המערכת)
            self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
            
            # 3. יצירת/טעינת ה"אוסף" (כמו טבלה בבסיס נתונים רגיל)
            self.collection = self.client.get_or_create_collection(
                name="japanika_menu",
                embedding_function=self.emb_fn
            )


    def ingest_data(self, csv_path):
        # טעינת הנתונים מהקובץ
        df = pd.read_csv(csv_path)
        
        # הכנת הרשימות להזרקה
        docs = df['תיאור_סמנטי_לחיפוש'].tolist()
        
        # יצירת מטא-דאטה (התגיות לסינון)
        metas = df.drop(columns=['תיאור_סמנטי_לחיפוש']).to_dict(orient='records')
        
        # יצירת מזהים ייחודיים (IDs) לכל מנה
        ids = [f"id_{i}" for i in range(len(df))]
        
        # הזרקה בפועל
        self.collection.upsert(
            documents=docs,
            metadatas=metas,
            ids=ids
        )

    def search(self, query_text, n_results=3, category_filter=None):
        # בניית פילטר במידה והמלצר בחר קטגוריה ספציפית
        where_clause = {}
        if category_filter:
            where_clause = {"קטגוריה": category_filter}
            
        # הרצת השאילתה הסמנטית
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_clause
        )
        return results