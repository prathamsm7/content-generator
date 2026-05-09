const BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type PostStatus = "pending" | "running" | "complete" | "error";

const TOKEN_KEY = "repurposely_token";

export type UserResponse = {
  user_id: string;
  email: string;
  display_name?: string;
};

export type TwitterPostPayload = {
  best_single_tweet: { text: string; selection_reason: string };
  best_thread: { tweets: string[]; selection_reason: string };
};

export type StepStatusMap = Partial<
  Record<"transcription" | "metadata" | "linkedin" | "twitter", "idle" | "running" | "complete" | "error">
>;

export type PostResponse = {
  post_id: string;
  status: PostStatus;
  error_message?: string | null;
  linkedin_post?: string;
  twitter_post?: TwitterPostPayload | null;
  ratings?: Record<string, { score: number; notes?: string | null }>;
  step_status?: StepStatusMap;
};

export type PostSummary = {
  post_id: string;
  url: string;
  title?: string;
  status: PostStatus;
  created_at?: string;
  platforms: string[];
};

export type ContentMutationResponse = {
  ok: boolean;
  platform: "linkedin" | "twitter";
  content: string | TwitterPostPayload;
  version_number: number;
  source: "generated" | "edited" | "regenerated" | string;
  feedback?: string | null;
};

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): HeadersInit {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return (j as { detail?: string }).detail || res.statusText;
  } catch {
    return await res.text();
  }
}

export async function createPost(url: string): Promise<{ post_id: string }> {
  const r = await fetch(`${BASE}/api/posts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function getPost(postId: string): Promise<PostResponse> {
  const r = await fetch(`${BASE}/api/posts/${postId}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function listPosts(): Promise<PostSummary[]> {
  const r = await fetch(`${BASE}/api/posts`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!r.ok) throw new Error(await parseError(r));
  const data = (await r.json()) as { posts: PostSummary[] };
  return data.posts;
}

export async function patchPostContent(
  postId: string,
  platform: "linkedin" | "twitter",
  content: string | TwitterPostPayload
): Promise<ContentMutationResponse> {
  const r = await fetch(`${BASE}/api/posts/${postId}/content`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ platform, content }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function ratePost(
  postId: string,
  platform: "linkedin" | "twitter",
  score: number,
  notes?: string
): Promise<{ ok: boolean; ratings: NonNullable<PostResponse["ratings"]> }> {
  const r = await fetch(`${BASE}/api/posts/${postId}/rate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ platform, score, notes }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function regeneratePost(
  postId: string,
  platform: "linkedin" | "twitter",
  feedback?: string
): Promise<ContentMutationResponse> {
  const r = await fetch(`${BASE}/api/posts/${postId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ platform, feedback }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export function getStreamUrl(postId: string): string {
  const token = getAuthToken();
  const encodedToken = token ? encodeURIComponent(token) : "";
  return `${BASE}/api/posts/${postId}/stream?token=${encodedToken}`;
}

export async function registerUser(
  email: string,
  password: string,
  displayName = ""
): Promise<{ access_token: string; user: UserResponse }> {
  const r = await fetch(`${BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function loginUser(
  email: string,
  password: string
): Promise<{ access_token: string; user: UserResponse }> {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}
