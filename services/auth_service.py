import flet as ft
from db import supabase

# [NEW] Authentication Service for Real Login

class AuthService:
    def __init__(self):
        self.current_user = None

    def sign_in(self, email, password):
        """Sign in with email and password via Supabase."""
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                self.current_user = res.user
                return res.user
            return None
        except Exception as e:
            print(f"Auth Error: {e}")
            raise e

    def sign_out(self):
        """Sign out the current user."""
        try:
            supabase.auth.sign_out()
            self.current_user = None
        except Exception as e:
            print(f"Sign Out Error: {e}")

    def get_user(self):
        """Get cached current user or fetch from session."""
        if self.current_user:
            return self.current_user
        
        # Check if session exists
        session = supabase.auth.get_session()
        if session and session.user:
            self.current_user = session.user
            return session.user
        return None

# Singleton Instance
auth_service = AuthService()
