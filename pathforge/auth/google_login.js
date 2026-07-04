/**
 * Supabase Google OAuth Login Module
 *
 * Usage:
 *   import { supabase, googleLogin, handleSession, getToken } from './google_login.js';
 *
 *   // Sign in with Google
 *   await googleLogin();
 *
 *   // On page load — restore session
 *   const session = await handleSession();
 *   if (session) {
 *     const token = session.access_token;
 *     // Use token in API calls: Authorization: Bearer <token>
 *   }
 */

// ── Configuration ─────────────────────────────────────────────────────────────
const SUPABASE_URL = "https://rrriujagbpfhrqzjcxfa.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJycml1amFnYnBmaHJxempjeGZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5Mzc2NTQsImV4cCI6MjA5NzUxMzY1NH0.dummy";

// ── Supabase Client ───────────────────────────────────────────────────────────
let _supabase = null;

async function getSupabase() {
  if (_supabase) return _supabase;
  const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2");
  _supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  });
  return _supabase;
}

// ── Sign In with Google ───────────────────────────────────────────────────────
async function googleLogin() {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin + "/auth/callback",
      queryParams: {
        access_type: "offline",
        prompt: "consent",
      },
    },
  });
  if (error) {
    console.error("Google login error:", error.message);
    return null;
  }
  // Browser will redirect to Google OAuth consent screen
  return data;
}

// ── Handle Session (call on page load) ────────────────────────────────────────
async function handleSession() {
  const supabase = await getSupabase();

  // Handle OAuth callback (URL contains #access_token=...)
  const hashParams = new URLSearchParams(window.location.hash.substring(1));
  if (hashParams.get("access_token")) {
    const { data, error } = await supabase.auth.setSession({
      access_token: hashParams.get("access_token"),
      refresh_token: hashParams.get("refresh_token"),
    });
    if (error) {
      console.error("Session restore error:", error.message);
      return null;
    }
    // Clean URL — remove hash fragment
    window.history.replaceState(null, "", window.location.pathname);
    return data.session;
  }

  // Check for existing session
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    console.error("Get session error:", error.message);
    return null;
  }
  return data.session;
}

// ── Sign Out ───────────────────────────────────────────────────────────────────
async function signOut() {
  const supabase = await getSupabase();
  const { error } = await supabase.auth.signOut();
  if (error) console.error("Sign out error:", error.message);
}

// ── Get Current Access Token ──────────────────────────────────────────────────
async function getToken() {
  const supabase = await getSupabase();
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token || null;
}

// ── Get Authenticated User ─────────────────────────────────────────────────────
async function getCurrentUser() {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.getUser();
  if (error) return null;
  return data.user;
}

// ── HTML Button Component ─────────────────────────────────────────────────────
function googleLoginButton(onClick) {
  const btn = document.createElement("button");
  btn.className = "google-login-btn";
  btn.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 48 48" style="margin-right:8px">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.54 28.59A14.51 14.51 0 0 1 9.5 24c0-1.59.28-3.14.76-4.59l-7.98-6.19A23.99 23.99 0 0 0 0 24c0 3.77.87 7.35 2.56 10.56l7.98-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.44-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
    Sign in with Google
  `;
  btn.style.cssText = `
    display: inline-flex; align-items: center; justify-content: center;
    padding: 10px 24px; border: 1px solid #dadce0; border-radius: 4px;
    background: white; color: #3c4043; font-size: 14px; font-weight: 500;
    font-family: 'Google Sans', Arial, sans-serif; cursor: pointer;
    transition: background 0.2s, box-shadow 0.2s;
  `;
  btn.addEventListener("mouseenter", () => {
    btn.style.background = "#f8f9fa";
    btn.style.boxShadow = "0 1px 3px rgba(0,0,0,0.1)";
  });
  btn.addEventListener("mouseleave", () => {
    btn.style.background = "white";
    btn.style.boxShadow = "none";
  });
  btn.addEventListener("click", onClick || googleLogin);
  return btn;
}

export {
  getSupabase,
  googleLogin,
  handleSession,
  signOut,
  getToken,
  getCurrentUser,
  googleLoginButton,
};
