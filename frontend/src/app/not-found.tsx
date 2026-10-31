import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6 text-center">
      <div className="max-w-md w-full bg-surface border border-border-subtle rounded-xl p-8 shadow-xs space-y-4">
        <span className="font-mono text-xs text-ink-muted uppercase tracking-wider">
          404 • Page Not Found
        </span>
        <h1 className="font-serif text-2xl font-semibold text-ink-primary">
          Specimen Not Located
        </h1>
        <p className="text-xs text-ink-secondary leading-relaxed">
          The biological module or study page you requested could not be found in the curriculum index.
        </p>
        <div className="pt-2">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Study Space</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

