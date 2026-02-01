import os
from dotenv import load_dotenv
from db import service_supabase

load_dotenv()

def check_names():
    print("--- User Name Mapping ---")
    ids = [
        "ce89c5a4-7f97-4900-a89e-18a713c7968f",
        "7662acf7-89a4-49b7-97ed-ad94a4a548aa",
        "0014c533-ad54-42a3-b2cf-b5eb49eae54e",
        "2666dfbc-5b43-478e-87c8-fd4e375c9b4b",
        "654167ec-bf71-4669-9a64-2b4f103174fd"
    ]
    
    res = service_supabase.table("profiles").select("id, full_name, username").in_("id", ids).execute()
    for u in res.data:
        print(f"ID: {u['id']} | Name: {u['full_name']} | Username: {u['username']}")

if __name__ == "__main__":
    check_names()
