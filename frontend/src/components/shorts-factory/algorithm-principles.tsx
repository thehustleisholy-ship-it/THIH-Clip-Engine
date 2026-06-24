import { ShieldCheck, Sparkles, Timer, Scissors } from "lucide-react";

const principles = [
  {
    icon: ShieldCheck,
    title: "Message Integrity First",
    body: "A clip should carry the sermon faithfully. No punchy edit is worth misrepresenting the message.",
  },
  {
    icon: Sparkles,
    title: "Opening Clarity",
    body: "The first three seconds must orient the viewer with conviction, tension, or a clear promise.",
  },
  {
    icon: Timer,
    title: "Complete Thought",
    body: "Favor moments with setup, payoff, and resolution. Avoid fragments that need hidden context.",
  },
  {
    icon: Scissors,
    title: "Distinct Windows",
    body: "Do not ship repeated clips from the same timestamp range. Pick fewer, stronger, separate moments.",
  },
];

export function AlgorithmPrinciples() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {principles.map((principle) => {
        const Icon = principle.icon;
        return (
          <div key={principle.title} className="border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-3">
              <span className="grid size-9 place-items-center bg-black text-[#d6b25e]">
                <Icon className="size-4" />
              </span>
              <h3 className="text-sm font-semibold text-neutral-950">{principle.title}</h3>
            </div>
            <p className="text-sm leading-6 text-neutral-600">{principle.body}</p>
          </div>
        );
      })}
    </div>
  );
}