import { ChatSession, ChatMessage } from "@/types/chat";

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  clinicalRole: string;
}

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

const AUTH_USER_KEY = "cardio_rag_current_user";

export const supabaseService = {
  isConfigured(): boolean {
    return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
  },

  getCurrentUser(): UserProfile | null {
    if (typeof window === "undefined") return null;
    try {
      const data = localStorage.getItem(AUTH_USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  async loginWithEmail(email: string, password?: string): Promise<UserProfile> {
    // For MVP production: creates or sets the active user session
    const user: UserProfile = {
      id: "usr_" + Math.random().toString(36).substring(2, 9),
      email,
      fullName: email.split("@")[0] || "Dr. User",
      clinicalRole: "Cardiology Specialist",
    };
    if (typeof window !== "undefined") {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    }
    return user;
  },

  async loginAsGuest(): Promise<UserProfile> {
    const guestUser: UserProfile = {
      id: "guest_" + Math.random().toString(36).substring(2, 9),
      email: "guest_clinician@cardiorag.app",
      fullName: "Guest Clinician",
      clinicalRole: "Guest Observer",
    };
    if (typeof window !== "undefined") {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(guestUser));
    }
    return guestUser;
  },

  logout(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem(AUTH_USER_KEY);
    }
  },
};
