from db import supabase
import uuid

def create_test_user():
    try:
        # 1. Check if any profile exists
        res = supabase.table("profiles").select("*").execute()
        if res.data:
            print(f"Existing profiles found: {len(res.data)}")
            print(f"Using first profile: {res.data[0]['username']}")
            return res.data[0]['id']
        
        # 2. Sign Up
        email = f"manager_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        print(f"Creating new test user: {email}")
        
        # Try passing dictionary vs kwargs based on library version differences
        try:
            auth_res = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
        except TypeError:
            # Fallback for different versions
            auth_res = supabase.auth.sign_up(email=email, password=password)
        
        # Check result
        # auth_res might be an object with .user or a dict
        user = getattr(auth_res, "user", None)
        if not user and isinstance(auth_res, dict):
            user = auth_res.get("user")
            
        if user:
            user_id = getattr(user, "id", None) or user.get("id")
            print(f"Auth User Created: {user_id}")
            
            # 3. Insert into profiles
            profile_data = {
                "id": user_id,
                "username": "점장님",
                "full_name": "The Manager"
            }
            supabase.table("profiles").insert(profile_data).execute()
            print("Profile created successfully!")
            return user_id
        else:
            print(f"Failed to create auth user. Response: {auth_res}")
            
    except Exception as e:
        print(f"CRITICAL ERROR in create_test_user: {e}")

if __name__ == "__main__":
    create_test_user()
