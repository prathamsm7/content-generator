"use client";

import { Brain, Check, Clock, FileText, MessageSquareText, WandSparkles } from "lucide-react";

export type StepKey = "transcription" | "metadata" | "linkedin" | "twitter";
export type StepState = "idle" | "active" | "done" | "error";

export function ProgressSteps({
  steps,
}: {
  steps: Record<StepKey, StepState>;
}) {
  const generating =
    steps.linkedin === "error" || steps.twitter === "error"
      ? "error"
      : steps.linkedin === "done" && steps.twitter === "done"
        ? "done"
        : steps.linkedin === "active" || steps.twitter === "active"
          ? "active"
          : "idle";

  const items = [
    {
      title: "Extracting metadata",
      description:
        steps.metadata === "done" ? "Completed" : steps.metadata === "active" ? "Reading video details..." : "Waiting...",
      state: steps.metadata,
      icon: FileText,
    },
    {
      title: "Transcribing audio",
      description:
        steps.transcription === "done"
          ? "Completed"
          : steps.transcription === "active"
            ? "Converting audio to text..."
            : "Waiting...",
      state: steps.transcription,
      icon: MessageSquareText,
    },
    {
      title: "Analyzing content",
      description:
        steps.metadata === "done" ? "Completed" : steps.metadata === "active" ? "Finding topics and tone..." : "Waiting...",
      state: steps.metadata,
      icon: Brain,
    },
    {
      title: "Generating posts",
      description:
        generating === "done" ? "Completed" : generating === "active" ? "Writing platform drafts..." : "Waiting...",
      state: generating,
      icon: WandSparkles,
    },
  ] as const;

  return (
    <div className="rounded-xl border border-[#55524b] bg-[#2c2c29] p-6 shadow-2xl">
      <div className="mb-6 flex items-center gap-3">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
        <h2 className="text-lg font-bold text-[#f7f4ee]">Processing your video</h2>
      </div>

      <ol className="space-y-5">
        {items.map(({ title, description, state, icon: Icon }) => {
          const active = state === "active";
          const done = state === "done";
          const error = state === "error";
          const bg = done
            ? "bg-green-800/70 text-green-100"
            : active
              ? "bg-blue-500/35 text-blue-100"
              : error
                ? "bg-red-500/50 text-red-100"
                : "bg-[#242421] text-[#c8c3b8]";
        return (
            <li key={title} className="flex items-center gap-4">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${bg}`}>
                {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-bold text-[#f7f4ee]">{title}</p>
                <p className="text-sm text-[#c8c3b8]">{description}</p>
              </div>
              {done && (
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-800 text-green-100">
                  <Check className="h-4 w-4" />
                </span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-6 flex items-center gap-2 rounded-lg bg-[#242421] px-4 py-3 text-sm font-semibold text-[#c8c3b8]">
        <Clock className="h-4 w-4" />
        Estimated time: 2-3 minutes
      </div>
    </div>
  );
}
