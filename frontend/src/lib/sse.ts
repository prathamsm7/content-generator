import { getStreamUrl } from "./api";

export type SseEvent =
  | { type: "step.start"; step: string }
  | { type: "step.complete"; step: string; output_preview?: string; phase?: string }
  | { type: "step.error"; step: string; message: string }
  | { type: "post.complete"; post: unknown }
  | { type: string; [k: string]: unknown };

export function subscribePostStream(
  postId: string,
  onEvent: (ev: SseEvent) => void,
  onDone?: () => void
): () => void {
  const url = getStreamUrl(postId);
  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as SseEvent;
      onEvent(data);
      if (data.type === "post.complete" || (data.type === "step.error" && (data as { step?: string }).step === "pipeline")) {
        es.close();
        onDone?.();
      }
    } catch {
      /* ignore parse errors */
    }
  };

  es.onerror = () => {
    es.close();
    onDone?.();
  };

  return () => es.close();
}
