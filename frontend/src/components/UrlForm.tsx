"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createPost } from "@/lib/api";
import { AtSign, BriefcaseBusiness, Camera, Newspaper, Sparkles, Video } from "lucide-react";

const YT_PATTERN =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|shorts\/)|youtu\.be\/)[\w-]{11}/i;

function looksLikeYoutubeUrl(url: string): boolean {
  const u = url.trim();
  if (!u) return false;
  return YT_PATTERN.test(u) || /youtu\.be\/[\w-]{11}/i.test(u) || /v=[\w-]{11}/.test(u);
}

export function UrlForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [style, setStyle] = useState<"professional" | "conversational" | "punchy">("professional");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!looksLikeYoutubeUrl(url)) {
      setErr("Enter a valid YouTube URL (watch, youtu.be, or shorts).");
      return;
    }
    setLoading(true);
    try {
      const { post_id } = await createPost(url.trim());
      router.push(`/posts/${post_id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to start post generation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-col gap-6">
      <div className="flex items-center gap-3">
        <Video className="h-5 w-5 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-[#f7f4ee]">Repurpose your YouTube video</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#c8c3b8]">
            Transform your YouTube content into platform-optimized posts for LinkedIn, Twitter, Medium,
            and more.
          </p>
        </div>
      </div>

      <label className="text-sm font-semibold text-[#f7f4ee]">
        YouTube URL
        <input
          type="url"
          name="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="mt-2 w-full rounded-lg border border-[#615e57] bg-[#31312e] px-3 py-2.5 text-base text-[#f7f4ee] shadow-sm outline-none placeholder:text-[#9b968c] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          disabled={loading}
          autoComplete="off"
        />
      </label>

      <div>
        <p className="text-sm font-semibold text-[#f7f4ee]">Select platforms</p>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-4">
          <PlatformPill checked icon={<BriefcaseBusiness className="h-4 w-4 text-sky-400" />} label="LinkedIn" />
          <PlatformPill checked icon={<AtSign className="h-4 w-4 text-zinc-200" />} label="Twitter/X" />
          <PlatformPill disabled icon={<Newspaper className="h-4 w-4 text-zinc-300" />} label="Medium" />
          <PlatformPill disabled icon={<Camera className="h-4 w-4 text-pink-400" />} label="Instagram" />
        </div>
        <p className="mt-2 text-xs text-[#9b968c]">POC currently generates LinkedIn and Twitter content.</p>
      </div>

      <div>
        <p className="text-sm font-semibold text-[#f7f4ee]">Content style</p>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <StyleButton
            active={style === "professional"}
            title="Professional"
            subtitle="Formal & data-driven"
            onClick={() => setStyle("professional")}
          />
          <StyleButton
            active={style === "conversational"}
            title="Conversational"
            subtitle="Casual & storytelling"
            onClick={() => setStyle("conversational")}
          />
          <StyleButton
            active={style === "punchy"}
            title="Punchy"
            subtitle="Bold & attention-grabbing"
            onClick={() => setStyle("punchy")}
          />
        </div>
      </div>

      {err && (
        <p className="text-sm text-red-400" role="alert">
          {err}
        </p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-lg border border-[#6a675f] bg-[#31312e] px-4 py-3 text-sm font-bold text-[#f7f4ee] shadow hover:bg-[#383833] disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4" />
        {loading ? "Starting..." : "Generate content"}
      </button>
    </form>
  );
}

function PlatformPill({
  checked,
  disabled,
  icon,
  label,
}: {
  checked?: boolean;
  disabled?: boolean;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm font-semibold ${
        disabled
          ? "border-[#55524b] text-[#9b968c] opacity-60"
          : "border-[#6a675f] bg-[#2f2f2c] text-[#f7f4ee]"
      }`}
    >
      <span className={`flex h-4 w-4 items-center justify-center rounded border text-xs ${
        checked ? "border-blue-400 bg-blue-500 text-white" : "border-[#8d887f]"
      }`}>
        {checked ? "✓" : ""}
      </span>
      {icon}
      <span>{label}</span>
    </div>
  );
}

function StyleButton({
  active,
  title,
  subtitle,
  onClick,
}: {
  active: boolean;
  title: string;
  subtitle: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border px-4 py-3 text-center ${
        active
          ? "border-blue-500 bg-blue-500/25 text-[#f7f4ee]"
          : "border-[#615e57] bg-[#2f2f2c] text-[#f7f4ee] hover:bg-[#383833]"
      }`}
    >
      <span className="block text-sm font-bold">{title}</span>
      <span className="mt-1 block text-xs text-[#c8c3b8]">{subtitle}</span>
    </button>
  );
}
