import React, { createContext, useContext, useEffect, useState } from "react";
import { DemoCredential, User } from "../types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthModalOpen: boolean;
  demoCredentials: DemoCredential[];
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  openAuthModal: () => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("custodian_token"));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [demoCredentials, setDemoCredentials] = useState<DemoCredential[]>([]);

  useEffect(() => {
    fetch("/api/v1/auth/demo-credentials")
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setDemoCredentials(data))
      .catch(() => setDemoCredentials([]));

    const storedToken = localStorage.getItem("custodian_token");
    if (storedToken) {
      fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${storedToken}` },
      })
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error("Invalid token");
        })
        .then((userData: User) => {
          setUser(userData);
          setToken(storedToken);
        })
        .catch(() => {
          localStorage.removeItem("custodian_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || err.error?.message || "Invalid username or password");
    }

    const data = await res.json();
    localStorage.setItem("custodian_token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    setIsAuthModalOpen(false);
  };

  const logout = async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // ignore
    }
    localStorage.removeItem("custodian_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthModalOpen,
        demoCredentials,
        login,
        logout,
        openAuthModal: () => setIsAuthModalOpen(true),
        closeAuthModal: () => setIsAuthModalOpen(false),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
