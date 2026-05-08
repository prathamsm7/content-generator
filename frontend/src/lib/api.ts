const BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type PostStatus = "pending" | "running" | "complete" | "error";

export type TwitterPostPayload = {
  best_single_tweet: { text: string; selection_reason: string };
  best_thread: { tweets: string[]; selection_reason: string };
};

export type StepStatusMap = Partial<
  Record<"transcription" | "metadata" | "linkedin" | "twitter", "idle" | "running" | "complete" | "error">
>;

export type PostResponse = {
  post_id: string;
  url: string;
  video_id: string;
  status: PostStatus;
  error_message?: string | null;
  title?: string;
  tags?: string[];
  video_context?: Record<string, unknown> | null;
  linkedin_post?: string;
  twitter_post?: TwitterPostPayload | null;
  ratings?: Record<string, { score: number; notes?: string | null }>;
  step_status?: StepStatusMap;
};

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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function getPost(postId: string): Promise<PostResponse> {
  const r = await fetch(`${BASE}/api/posts/${postId}`, { cache: "no-store" });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function patchPostContent(
  postId: string,
  platform: "linkedin" | "twitter",
  content: string | TwitterPostPayload
): Promise<{ ok: boolean; post: PostResponse }> {
  const r = await fetch(`${BASE}/api/posts/${postId}/content`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
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
): Promise<{ ok: boolean; ratings: Record<string, unknown> }> {
  const r = await fetch(`${BASE}/api/posts/${postId}/rate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform, score, notes }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function regeneratePost(
  postId: string,
  platform: "linkedin" | "twitter"
): Promise<{ ok: boolean; post: PostResponse }> {
  const r = await fetch(`${BASE}/api/posts/${postId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform }),
  });
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export function getStreamUrl(postId: string): string {
  return `${BASE}/api/posts/${postId}/stream`;
}
