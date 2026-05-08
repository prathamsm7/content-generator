"use client";

import { ContentCard } from "@/components/ContentCard";
import { ProgressSteps, type StepKey, type StepState } from "@/components/ProgressSteps";
import { getPost, type PostResponse, type StepStatusMap } from "@/lib/api";
import { subscribePostStream, type SseEvent } from "@/lib/sse";
import { AtSign, BarChart3, BriefcaseBusiness } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const STEP_KEYS: StepKey[] = ["transcription", "metadata", "linkedin", "twitter"];

function mapStepStatus(raw: StepStatusMap | undefined): Record<StepKey, StepState> {
  const output = {} as Record<StepKey, StepState>;
  for (const key of STEP_KEYS) {
    const value = raw?.[key] ?? "idle";
    if (value === "running") output[key] = "active";
    else if (value === "complete") output[key] = "done";
    else if (value === "error") output[key] = "error";
    else output[key] = "idle";
  }
  return output;
}

function allDone(): Record<StepKey, StepState> {
  const output = {} as Record<StepKey, StepState>;
  for (const key of STEP_KEYS) output[key] = "done";
  return output;
}

export default function PostPage() {
  const params = useParams();
  const postId = params.id as string;
  const [post, setPost] = useState<PostResponse | null>(null);
  const [steps, setSteps] = useState<Record<StepKey, StepState>>(() => {
    const output = {} as Record<StepKey, StepState>;
    for (const key of STEP_KEYS) output[key] = "idle";
    return output;
  });
  const [loadError, setLoadError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activePlatform, setActivePlatform] = useState<"linkedin" | "twitter">("linkedin");

  const onPostUpdated = useCallback((updatedPost: PostResponse) => {
    setPost(updatedPost);
    setSteps(mapStepStatus(updatedPost.step_status));
  }, []);

  useEffect(() => {
    let cancelled = false;
    let closeSse: (() => void) | undefined;

    setLoadError(null);
    setStreamError(null);

    (async () => {
      try {
        const loadedPost = await getPost(postId);
        if (cancelled) return;

        setPost(loadedPost);
        setSteps(mapStepStatus(loadedPost.step_status));

        if (loadedPost.status === "complete" || loadedPost.status === "error") return;

        closeSse = subscribePostStream(postId, async (event: SseEvent) => {
          if (event.type === "step.start" && typeof event.step === "string") {
            setSteps((currentSteps) => ({
              ...currentSteps,
              [event.step as StepKey]: "active",
            }));
            setPost((currentPost) =>
              currentPost && currentPost.status === "pending"
                ? { ...currentPost, status: "running" }
                : currentPost
            );
          }

          if (event.type === "step.complete" && typeof event.step === "string") {
            setSteps((currentSteps) => ({
              ...currentSteps,
              [event.step as StepKey]: "done",
            }));
          }

          if (event.type === "step.error") {
            const message = typeof event.message === "string" ? event.message : "Pipeline error";
            setStreamError(message);
            try {
              const freshPost = await getPost(postId);
              if (!cancelled) {
                setPost(freshPost);
                setSteps(mapStepStatus(freshPost.step_status));
              }
            } catch {
              /* ignore refresh errors */
            }
          }

          if (event.type === "post.complete" && event.post && typeof event.post === "object") {
            setPost(event.post as PostResponse);
            setSteps(allDone());
            setStreamError(null);
          }
        });
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "Failed to load post");
        }
      }
    })();

    return () => {
      cancelled = true;
      closeSse?.();
    };
  }, [postId]);

  if (loadError) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <p className="text-red-400">{loadError}</p>
        <Link href="/" className="mt-4 inline-block text-blue-400 underline">
          Back home
        </Link>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <p className="text-[#c8c3b8]">Loading post...</p>
      </div>
    );
  }

  const showResults = post.status === "complete" && post.linkedin_post && post.twitter_post;
  const showProgress = !showResults && post.status !== "error";

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      {(post.status === "error" || streamError) && (
        <div
          className="rounded-xl border border-red-900 bg-red-950/70 p-4 text-sm text-red-100"
          role="alert"
        >
          <strong className="font-semibold">Something went wrong.</strong>
          <p className="mt-1">{post.error_message || streamError}</p>
          <p className="mt-2 text-xs text-red-300">
            Check that the video has captions, the URL is valid, and your API key is set on the server.
          </p>
        </div>
      )}

      {showProgress && (
        <div className="mt-8">
          <ProgressSteps steps={steps} />
        </div>
      )}

      {showResults && (
        <div className="flex flex-col gap-5">
          <div className="flex border-b border-[#47443e]">
            <TabButton
              active={activePlatform === "linkedin"}
              onClick={() => setActivePlatform("linkedin")}
              icon={<BriefcaseBusiness className="h-4 w-4" />}
              label="LinkedIn"
            />
            <TabButton
              active={activePlatform === "twitter"}
              onClick={() => setActivePlatform("twitter")}
              icon={<AtSign className="h-4 w-4" />}
              label="Twitter"
            />
            <TabButton disabled label="Medium" />
          </div>

          <ContentCard
            postId={postId}
            platform={activePlatform}
            post={post}
            onPostUpdated={onPostUpdated}
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Link
              href="/"
              className="flex items-center justify-center gap-2 rounded-lg border border-[#55524b] bg-[#2c2c29] px-4 py-3 text-sm font-bold text-[#f7f4ee] hover:bg-[#383833]"
            >
              ← Process another video
            </Link>
            <button
              type="button"
              className="flex items-center justify-center gap-2 rounded-lg border border-[#55524b] bg-[#2c2c29] px-4 py-3 text-sm font-bold text-[#f7f4ee] opacity-70"
              disabled
            >
              <BarChart3 className="h-4 w-4" />
              View analytics
            </button>
          </div>
        </div>
      )}

      {(post.status === "running" || post.status === "pending") && !showResults && !streamError && (
        <p className="mt-6 text-sm text-[#9b968c]">This can take a minute depending on video length...</p>
      )}
    </main>
  );
}

function TabButton({
  active,
  disabled,
  icon,
  label,
  onClick,
}: {
  active?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-bold ${
        active
          ? "border-[#f7f4ee] text-[#f7f4ee]"
          : "border-transparent text-[#c8c3b8] hover:text-[#f7f4ee]"
      } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
    >
      {icon}
      {label}
    </button>
  );
}
