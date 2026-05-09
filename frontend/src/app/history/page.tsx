"use client";

import { clearAuthToken, getAuthToken, listPosts, type PostSummary } from "@/lib/api";
import { Clock, LogOut, Plus, Video } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function HistoryPage() {
  const router = useRouter();
  const [posts, setPosts] = useState<PostSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAuthToken()) {
      router.replace("/login");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const items = await listPosts();
        if (!cancelled) setPosts(items);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load history");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [router]);

  function logout() {
    clearAuthToken();
    router.replace("/login");
  }

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#f7f4ee]">Post history</h1>
          <p className="mt-1 text-sm text-[#c8c3b8]">Every generated video and its versioned drafts.</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833]"
          >
            <Plus className="h-4 w-4" />
            New post
          </Link>
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833]"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-[#c8c3b8]">Loading history...</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && !error && posts.length === 0 && (
        <div className="rounded-xl border border-[#55524b] bg-[#2c2c29] p-6 text-center">
          <Video className="mx-auto h-8 w-8 text-blue-400" />
          <p className="mt-3 font-bold text-[#f7f4ee]">No posts yet</p>
          <p className="mt-1 text-sm text-[#c8c3b8]">Generate your first post from a YouTube URL.</p>
        </div>
      )}

      <div className="grid gap-3">
        {posts.map((post) => (
          <Link
            key={post.post_id}
            href={`/posts/${post.post_id}`}
            className="rounded-xl border border-[#55524b] bg-[#2c2c29] p-4 hover:bg-[#33332f]"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-bold text-[#f7f4ee]">{post.title || "Untitled video"}</p>
                <p className="mt-1 line-clamp-1 text-sm text-[#9b968c]">{post.url}</p>
              </div>
              <span className="rounded-full border border-[#6a675f] px-3 py-1 text-xs font-bold uppercase text-[#c8c3b8]">
                {post.status}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-[#9b968c]">
              <span>{post.platforms.length ? post.platforms.join(", ") : "No drafts yet"}</span>
              {post.created_at && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {new Date(post.created_at).toLocaleString()}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
