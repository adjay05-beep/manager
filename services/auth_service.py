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
                
                # [FIX] Auto-create profile if it doesn't exist (same as verify_otp)
                try:
                    profile_check = supabase.table("profiles").select("id").eq("id", res.user.id).execute()
                    if not profile_check.data:
                        # Create profile for existing user without one
                        full_name = res.user.user_metadata.get("full_name", email.split("@")[0])
                        supabase.table("profiles").insert({
                            "id": res.user.id,
                            "full_name": full_name,
                            "role": "staff"
                        }).execute()
                        print(f"DEBUG: Auto-created profile for user {res.user.id} during login")
                except Exception as profile_err:
                    print(f"WARNING: Failed to auto-create profile during login: {profile_err}")
                    # Don't fail the login if profile creation fails
                
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

    def sign_up(self, email, password, full_name):
        """Register a new user."""
        try:
            # Send metadata (full_name) to be stored in profiles trigger or raw user_metadata
            options = {"data": {"full_name": full_name}}
            res = supabase.auth.sign_up({"email": email, "password": password, "options": options})
            return res
        except Exception as e:
            msg = str(e)
            if "User already registered" in msg:
                raise Exception("이미 가입된 이메일입니다.")
            raise e

    def verify_otp(self, email, token, type="signup"):
        """Verify email using OTP code."""
        try:
            res = supabase.auth.verify_otp({"email": email, "token": token, "type": type})
            if res.user:
                self.current_user = res.user
                
                # [FIX] Auto-create profile if it doesn't exist
                # Check if profile exists
                try:
                    profile_check = supabase.table("profiles").select("id").eq("id", res.user.id).execute()
                    if not profile_check.data:
                        # Create profile for new user
                        full_name = res.user.user_metadata.get("full_name", email.split("@")[0])
                        supabase.table("profiles").insert({
                            "id": res.user.id,
                            "full_name": full_name,
                            "role": "staff"
                        }).execute()
                        print(f"DEBUG: Created profile for user {res.user.id}")
                except Exception as profile_err:
                    print(f"WARNING: Failed to create profile: {profile_err}")
                    # Don't fail the entire verification if profile creation fails
                
                return res.user
            return None
        except Exception as e:
            raise Exception(f"인증 실패: {e}")

    def resend_otp(self, email):
        """Resend status/OTP."""
        try:
            # 'signup' type forces resend of the confirmation mail
            supabase.auth.resend({"type": "signup", "email": email})
        except Exception as e:
            print(f"Resend Error: {e}")

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
