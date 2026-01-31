from repositories.auth_repository import AuthRepository
from utils.logger import log_error, log_info

# [PROFESSIONAL] Refactored to use Repository Pattern

class AuthService:
    def __init__(self):
        self.current_user = None

    def sign_in(self, email, password):
        """Sign in with email and password."""
        try:
            res = AuthRepository.sign_in(email, password)
            if res.user:
                self.current_user = res.user
                
                # Auto-ensure profile exists
                try:
                    full_name = res.user.user_metadata.get("full_name", email.split("@")[0])
                    role = res.user.user_metadata.get("role", "staff")
                    AuthRepository.upsert_profile({
                        "id": res.user.id,
                        "full_name": full_name,
                        "role": role
                    })
                    log_info(f"Profile verified for user {res.user.id}")
                except Exception as profile_err:
                    log_error(f"Failed to ensure profile during login: {profile_err}")
                
                return res
            return None
        except Exception as e:
            log_error(f"Auth Service Error (sign_in): {e}")
            raise e

    def sign_out(self):
        """Sign out the current user."""
        try:
            AuthRepository.sign_out()
            self.current_user = None
        except Exception as e:
            log_error(f"Sign Out Error: {e}")

    def sign_up(self, email, password, full_name, role="staff"):
        """Register a new user."""
        try:
            options = {"data": {"full_name": full_name, "role": role}}
            return AuthRepository.sign_up(email, password, options=options)
        except Exception as e:
            msg = str(e)
            if "User already registered" in msg:
                raise Exception("이미 가입된 이메일입니다.")
            raise e

    def verify_otp(self, email, token, type="signup"):
        """Verify email using OTP code."""
        try:
            res = AuthRepository.verify_otp(email, token, otp_type=type)
            if res.user:
                self.current_user = res.user
                # [FIX] Auto-create profile
                full_name = res.user.user_metadata.get("full_name", email.split("@")[0])
                role = res.user.user_metadata.get("role", "staff")
                AuthRepository.upsert_profile({"id": res.user.id, "full_name": full_name, "role": role})
                return res.user
            return None
        except Exception as e:
            raise Exception(f"인증 실패: {e}")

    def get_user_role(self, user_id):
        """Fetch user role from profiles."""
        profile = AuthRepository.get_user_profile(user_id)
        return profile.get("role", "staff") if profile else "staff"

    def resend_otp(self, email):
        """Resend OTP."""
        try:
            AuthRepository.resend_otp(email)
        except Exception as e:
            log_error(f"Resend Error: {e}")

    def get_user(self):
        """Get cached current user or fetch from session."""
        if self.current_user:
            return self.current_user
        
        session = AuthRepository.get_session()
        if session and session.user:
            self.current_user = session.user
            return session.user
        return None

    def get_access_token(self):
        """Retrieve a valid access token."""
        try:
            session = AuthRepository.get_session()
            return session.access_token if session else None
        except Exception as e:
            log_error(f"Failed to get access token: {e}")
            return None

    def get_session(self):
        """Return the current session object."""
        return AuthRepository.get_session()

    def refresh_session(self, refresh_token_str):
        """Refresh session using refresh_token."""
        try:
            res = AuthRepository.refresh_session(refresh_token_str)
            if res.user:
                self.current_user = res.user
                return res
            return None
        except Exception as e:
            log_error(f"Token Refresh Failed: {e}")
            return None

    def recover_session(self, access_token, refresh_token):
        """Recover session from stored tokens."""
        try:
            res = AuthRepository.set_session(access_token, refresh_token)
            if res.user:
                self.current_user = res.user
                return res.user
            return None
        except Exception as e:
            log_error(f"Session Recovery Failed: {e}")
            return None

    def get_auth_headers(self):
        """Get headers for authenticated Supabase requests."""
        token = self.get_access_token()
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "apikey": AuthRepository.service_supabase.key # Required by postgrest
            }
        return None

# Singleton Instance
auth_service = AuthService()

