"use client";

import { Clipboard, Check } from "lucide-react";

import { buildManualClippingBrief, buildSelectionInstructions, type SermonMetadata } from "@/lib/shorts-factory";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface AIInstructionsProps {
  metadata: SermonMetadata;
  copiedKey: string | null;
  onCopy: (key: string, value: string) => void;
}

export function AIInstructions({ metadata, copiedKey, onCopy }: AIInstructionsProps) {
  const selectionInstructions = buildSelectionInstructions(metadata);
  const manualBrief = buildManualClippingBrief(metadata);

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="border border-neutral-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-neutral-950">Selection instructions</h3>
            <p className="mt-1 text-xs text-neutral-500">Saved task instructions feed future AI analysis and resume runs.</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => onCopy("selection-instructions", selectionInstructions)}>
            {copiedKey === "selection-instructions" ? <Check className="size-4" /> : <Clipboard className="size-4" />}
            Copy
          </Button>
        </div>
        <Textarea readOnly value={selectionInstructions} className="min-h-72 font-mono text-xs leading-5" />
      </section>

      <section className="border border-neutral-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-neutral-950">Manual clipping brief</h3>
            <p className="mt-1 text-xs text-neutral-500">Use this packet when hand-reviewing sermon moments before publishing.</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => onCopy("manual-brief", manualBrief)}>
            {copiedKey === "manual-brief" ? <Check className="size-4" /> : <Clipboard className="size-4" />}
            Copy
          </Button>
        </div>
        <Textarea readOnly value={manualBrief} className="min-h-72 font-mono text-xs leading-5" />
      </section>
    </div>
  );
}
