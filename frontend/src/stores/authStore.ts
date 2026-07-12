import { create } from 'zustand';

interface User {
  id: string;
  name: string;
  role: string;
  team_id?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  token: string | null;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  token: null,
  login: async (username, password) => {
    // Mock login for now
    set({
      user: { id: '1', name: username, role: 'Admin', team_id: 'team-alpha' },
      isAuthenticated: true,
      token: 'mock-jwt-token'
    });
  },
  logout: () => set({ user: null, isAuthenticated: false, token: null }),
}));
