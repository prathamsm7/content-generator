"use client";

import { ContentCard } from "@/components/ContentCard";
import { ProgressSteps, type StepKey, type StepState } from "@/components/ProgressSteps";
import { getJob, type JobResponse, type StepStatusMap } from "@/lib/api";
import { subscribeJobStream, type SseEvent } from "@/lib/sse";
import { AtSign, BarChart3, BriefcaseBusiness } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const STEP_KEYS: StepKey[] = ["transcription", "metadata", "linkedin", "twitter"];

function mapStepStatus(raw: StepStatusMap | undefined): Record<StepKey, StepState> {
  const out = {} as Record<StepKey, StepState>;
  for (const k of STEP_KEYS) {
    const v = raw?.[k] ?? "idle";
    if (v === "running") out[k] = "active";
    else if (v === "complete") out[k] = "done";
    else if (v === "error") out[k] = "error";
    else out[k] = "idle";
  }
  return out;
}

function allDone(): Record<StepKey, StepState> {
  const out = {} as Record<StepKey, StepState>;
  for (const k of STEP_KEYS) out[k] = "done";
  return out;
}

export default function JobPage() {
  const params = useParams();
  const id = params.id as string;
  const [job, setJob] = useState<JobResponse | null>(null);
  const [steps, setSteps] = useState<Record<StepKey, StepState>>(() => {
    const o = {} as Record<StepKey, StepState>;
    for (const k of STEP_KEYS) o[k] = "idle";
    return o;
  });
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [streamErr, setStreamErr] = useState<string | null>(null);
  const [activePlatform, setActivePlatform] = useState<"linkedin" | "twitter">("linkedin");

  const onJobUpdated = useCallback((j: JobResponse) => {
    setJob(j);
    setSteps(mapStepStatus(j.step_status));
  }, []);

  useEffect(() => {
    let cancelled = false;
    let closeSse: (() => void) | undefined;

    setLoadErr(null);
    setStreamErr(null);

    (async () => {
      try {
        const j = await getJob(id);
        if (cancelled) return;
        setJob(j);
        setSteps(mapStepStatus(j.step_status));

        if (j.status === "complete" || j.status === "error") return;

        closeSse = subscribeJobStream(id, async (ev: SseEvent) => {
          if (ev.type === "step.start" && typeof ev.step === "string") {
            setSteps((s) => ({ ...s, [ev.step as StepKey]: "active" }));
            setJob((prev) => (prev && prev.status === "pending" ? { ...prev, status: "running" } : prev));
          }
          if (ev.type === "step.complete" && typeof ev.step === "string") {
            setSteps((s) => ({ ...s, [ev.step as StepKey]: "done" }));
          }
          if (ev.type === "step.error") {
            const msg = typeof ev.message === "string" ? ev.message : "Pipeline error";
            setStreamErr(msg);
            try {
              const fresh = await getJob(id);
              if (!cancelled) {
                setJob(fresh);
                setSteps(mapStepStatus(fresh.step_status));
              }
            } catch {
              /* ignore */
            }
          }
          if (ev.type === "job.complete" && ev.job && typeof ev.job === "object") {
            setJob(ev.job as JobResponse);
            setSteps(allDone());
            setStreamErr(null);
          }
        });
      } catch (e) {
        if (!cancelled) setLoadErr(e instanceof Error ? e.message : "Failed to load job");
      }
    })();

    return () => {
      cancelled = true;
      closeSse?.();
    };
  }, [id]);

  if (loadErr) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <p className="text-red-400">{loadErr}</p>
        <Link href="/" className="mt-4 inline-block text-blue-400 underline">
          Back home
        </Link>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <p className="text-[#c8c3b8]">Loading job...</p>
      </div>
    );
  }

  const showResults = job.status === "complete" && job.linkedin_post && job.twitter_post;
  const showProgress = !showResults && job.status !== "error";

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">

      {(job.status === "error" || streamErr) && (
        <div
          className="rounded-xl border border-red-900 bg-red-950/70 p-4 text-sm text-red-100"
          role="alert"
        >
          <strong className="font-semibold">Something went wrong.</strong>
          <p className="mt-1">{job.error_message || streamErr}</p>
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

          <ContentCard jobId={id} platform={activePlatform} job={job} onJobUpdated={onJobUpdated} />

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

      {(job.status === "running" || job.status === "pending") && !showResults && !streamErr && (
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
