"use client";

import { useCallback, useState } from "react";
import {
  patchPostContent,
  ratePost,
  regeneratePost,
  type PostResponse,
  type TwitterPostPayload,
} from "@/lib/api";
import { Copy, RefreshCw, Send } from "lucide-react";

type Platform = "linkedin" | "twitter";

function mergeContentUpdate(
  post: PostResponse,
  platform: Platform,
  content: string | TwitterPostPayload
): PostResponse {
  if (platform === "linkedin") {
    return { ...post, linkedin_post: content as string };
  }
  return { ...post, twitter_post: content as TwitterPostPayload };
}

export function ContentCard({
  postId,
  platform,
  post,
  onPostUpdated,
}: {
  postId: string;
  platform: Platform;
  post: PostResponse;
  onPostUpdated: (post: PostResponse) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [regen, setRegen] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const rating = post.ratings?.[platform]?.score ?? 0;

  const linkedinText = post.linkedin_post ?? "";
  const twitter: TwitterPostPayload | null = post.twitter_post ?? null;

  const saveLinkedIn = useCallback(
    async (text: string) => {
      setSaving(true);
      setErr(null);
      try {
        const result = await patchPostContent(postId, "linkedin", text);
        onPostUpdated(mergeContentUpdate(post, "linkedin", result.content));
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Save failed");
      } finally {
        setSaving(false);
      }
    },
    [postId, post, onPostUpdated]
  );

  const saveTwitter = useCallback(
    async (payload: TwitterPostPayload) => {
      setSaving(true);
      setErr(null);
      try {
        const result = await patchPostContent(postId, "twitter", payload);
        onPostUpdated(mergeContentUpdate(post, "twitter", result.content));
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Save failed");
      } finally {
        setSaving(false);
      }
    },
    [postId, post, onPostUpdated]
  );

  async function onRate(score: number) {
    setErr(null);
    try {
      const result = await ratePost(postId, platform, score);
      onPostUpdated({ ...post, ratings: result.ratings });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Rating failed");
    }
  }

  async function onRegenerate(feedback?: string) {
    setRegen(true);
    setErr(null);
    try {
      const result = await regeneratePost(postId, platform, feedback);
      onPostUpdated(mergeContentUpdate(post, platform, result.content));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Regenerate failed");
    } finally {
      setRegen(false);
    }
  }

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      setErr("Could not copy to clipboard");
    }
  }

  const feedbackChips = ["Too formal", "Too casual", "Too long", "Too generic", "Needs more personality"];

  if (platform === "linkedin") {
    return (
      <section className="rounded-xl border border-[#55524b] bg-[#2c2c29] p-5 shadow-2xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-[#f7f4ee]">LinkedIn post</h2>
            <span className="rounded-full bg-[#242421] px-2 py-1 text-xs font-bold text-[#c8c3b8]">
              {linkedinText.length.toLocaleString()} characters
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => copyText(linkedinText)}
              className="flex items-center gap-2 rounded-lg border border-[#6a675f] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833]"
            >
              <Copy className="h-4 w-4" />
              Copy
            </button>
          </div>
        </div>
        {err && <p className="mb-2 text-sm text-red-400">{err}</p>}
        <textarea
          key={linkedinText.slice(0, 40)}
          defaultValue={linkedinText}
          onBlur={(e) => {
            if (e.target.value !== linkedinText) void saveLinkedIn(e.target.value);
          }}
          rows={14}
          className="w-full resize-y rounded-lg border border-[#615e57] bg-[#31312e] p-4 font-sans text-sm font-semibold leading-7 text-[#f7f4ee] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          disabled={regen}
        />
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => onRegenerate()}
            disabled={regen}
            className="flex items-center justify-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-3 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833] disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${regen ? "animate-spin" : ""}`} />
            {regen ? "Regenerating..." : "Regenerate"}
          </button>
          <button
            type="button"
            className="flex items-center justify-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-3 text-sm font-bold text-[#f7f4ee] opacity-80"
            disabled
          >
            <Send className="h-4 w-4" />
            Publish to LinkedIn
          </button>
        </div>

        <div className="mt-5 border-t border-[#47443e] pt-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm font-bold text-[#c8c3b8]">Rate this draft:</span>
            {[1, 2, 3, 4, 5].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onRate(s)}
                className={`text-lg ${rating >= s ? "text-amber-400" : "text-[#6a675f]"}`}
                aria-label={`Rate ${s}`}
              >
                ★
              </button>
            ))}
            {saving && <span className="text-xs text-[#9b968c]">Saving...</span>}
          </div>
          <p className="mb-3 text-sm font-bold text-[#c8c3b8]">Not quite right? Tell us what to improve:</p>
          <div className="flex flex-wrap gap-2">
            {feedbackChips.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => onRegenerate(chip)}
                disabled={regen}
                className="rounded-lg border border-[#6a675f] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833] disabled:opacity-50"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      </section>
    );
  }

  /* Twitter */
  const tw = twitter || {
    best_single_tweet: { text: "", selection_reason: "" },
    best_thread: { tweets: [] as string[], selection_reason: "" },
  };

  return (
    <section className="rounded-xl border border-[#55524b] bg-[#2c2c29] p-5 shadow-2xl">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="font-bold text-[#f7f4ee]">Twitter/X content</h2>
          <span className="rounded-full bg-[#242421] px-2 py-1 text-xs font-bold text-[#c8c3b8]">
            Single + thread
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              copyText(
                [tw.best_single_tweet.text, "", ...tw.best_thread.tweets].join("\n\n")
              )
            }
            className="flex items-center gap-2 rounded-lg border border-[#6a675f] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833]"
          >
            <Copy className="h-4 w-4" />
            Copy all
          </button>
        </div>
      </div>
      {err && <p className="mb-2 text-sm text-red-400">{err}</p>}

      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-[#c8c3b8]">Single tweet</p>
      <textarea
        key={tw.best_single_tweet.text.slice(0, 30)}
        defaultValue={tw.best_single_tweet.text}
        onBlur={(e) => {
          const next: TwitterPostPayload = {
            ...tw,
            best_single_tweet: {
              ...tw.best_single_tweet,
              text: e.target.value,
            },
          };
          if (JSON.stringify(next) !== JSON.stringify(tw)) void saveTwitter(next);
        }}
        rows={4}
        className="mb-4 w-full resize-y rounded-lg border border-[#615e57] bg-[#31312e] p-4 text-sm font-semibold leading-7 text-[#f7f4ee] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        disabled={regen}
      />

      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-[#c8c3b8]">Thread (one tweet per line)</p>
      <textarea
        key={tw.best_thread.tweets.join("\n").slice(0, 40)}
        defaultValue={tw.best_thread.tweets.join("\n")}
        onBlur={(e) => {
          const lines = e.target.value
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean);
          const next: TwitterPostPayload = {
            ...tw,
            best_thread: {
              ...tw.best_thread,
              tweets: lines,
            },
          };
          if (JSON.stringify(next) !== JSON.stringify(tw)) void saveTwitter(next);
        }}
        rows={10}
        className="w-full resize-y rounded-lg border border-[#615e57] bg-[#31312e] p-4 font-mono text-sm font-semibold leading-7 text-[#f7f4ee] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        disabled={regen}
      />

      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onRegenerate()}
          disabled={regen}
          className="flex items-center justify-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-3 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833] disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${regen ? "animate-spin" : ""}`} />
          {regen ? "Regenerating..." : "Regenerate"}
        </button>
        <button
          type="button"
          className="flex items-center justify-center gap-2 rounded-lg border border-[#6a675f] bg-[#2f2f2c] px-4 py-3 text-sm font-bold text-[#f7f4ee] opacity-80"
          disabled
        >
          <Send className="h-4 w-4" />
          Publish to X
        </button>
      </div>

      <div className="mt-5 border-t border-[#47443e] pt-4">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-sm font-bold text-[#c8c3b8]">Rate this draft:</span>
          {[1, 2, 3, 4, 5].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onRate(s)}
              className={`text-lg ${rating >= s ? "text-amber-400" : "text-[#6a675f]"}`}
              aria-label={`Rate ${s}`}
            >
              ★
            </button>
          ))}
          {saving && <span className="text-xs text-[#9b968c]">Saving...</span>}
        </div>
        <p className="mb-3 text-sm font-bold text-[#c8c3b8]">Not quite right? Tell us what to improve:</p>
        <div className="flex flex-wrap gap-2">
          {feedbackChips.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => onRegenerate(chip)}
              disabled={regen}
              className="rounded-lg border border-[#6a675f] px-4 py-2 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833] disabled:opacity-50"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
