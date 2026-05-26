"use client";

import { useState } from "react";
import { Shield, Loader2, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store";

export function LoginScreen() {
  const { setAuth } = useAppStore();
  const [email, setEmail] = useState("admin@copilot.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.login(email, password);
      const user = await api.getMe();
      setAuth(user, res.access_token);
    } catch (e: any) {
      setError(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex items-center justify-center px-4" style={{ background: "radial-gradient(ellipse at 50% 30%, rgba(99,102,241,0.08), transparent 60%)" }}>
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-accent/10 flex items-center justify-center border border-accent/20">
            <Zap className="w-7 h-7 text-accent" />
          </div>
          <h1 className="text-2xl font-display text-text-primary">
            Offline Copilot
          </h1>
          <p className="text-sm text-text-secondary">
            Air-gapped enterprise AI assistant
          </p>
        </div>

        {/* Form */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-text-muted mb-1.5 tracking-wide uppercase">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-surface-raised border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-colors"
              placeholder="admin@copilot.local"
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1.5 tracking-wide uppercase">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              className="w-full px-3.5 py-2.5 bg-surface-raised border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs text-center">{error}</p>
          )}

          <button
            onClick={handleLogin}
            disabled={loading || !password}
            className="w-full py-2.5 bg-accent hover:bg-accent/90 disabled:bg-accent/40 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </div>

        <p className="text-center text-xs text-text-muted">
          Secured with JWT • RBAC • Audit Logging
        </p>
      </div>
    </div>
  );
}
