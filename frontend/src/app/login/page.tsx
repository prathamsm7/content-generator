"use client";

import { loginUser, registerUser, setAuthToken } from "@/lib/api";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response =
        mode === "login"
          ? await loginUser(email, password)
          : await registerUser(email, password, displayName);
      setAuthToken(response.access_token);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10">
      <form onSubmit={onSubmit} className="w-full rounded-xl border border-[#55524b] bg-[#2c2c29] p-6 shadow-2xl">
        <div className="mb-6 flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-blue-400" />
          <div>
            <h1 className="text-xl font-bold text-[#f7f4ee]">
              {mode === "login" ? "Sign in to Repurposely" : "Create your account"}
            </h1>
            <p className="mt-1 text-sm text-[#c8c3b8]">Save drafts, versions, ratings, and history.</p>
          </div>
        </div>

        {mode === "register" && (
          <label className="mb-4 block text-sm font-semibold text-[#f7f4ee]">
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-2 w-full rounded-lg border border-[#615e57] bg-[#31312e] px-3 py-2.5 text-[#f7f4ee] outline-none focus:border-blue-500"
              placeholder="Pratham"
            />
          </label>
        )}

        <label className="mb-4 block text-sm font-semibold text-[#f7f4ee]">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-2 w-full rounded-lg border border-[#615e57] bg-[#31312e] px-3 py-2.5 text-[#f7f4ee] outline-none focus:border-blue-500"
            placeholder="you@example.com"
            required
          />
        </label>

        <label className="mb-4 block text-sm font-semibold text-[#f7f4ee]">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full rounded-lg border border-[#615e57] bg-[#31312e] px-3 py-2.5 text-[#f7f4ee] outline-none focus:border-blue-500"
            placeholder="At least 8 characters"
            required
          />
        </label>

        {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg border border-[#6a675f] bg-[#31312e] px-4 py-3 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833] disabled:opacity-50"
        >
          {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="mt-4 w-full text-sm font-semibold text-blue-300 hover:text-blue-200"
        >
          {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
        </button>
      </form>
    </main>
  );
}
