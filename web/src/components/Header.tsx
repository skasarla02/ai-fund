export function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-[60] flex h-16 items-center border-b border-white/6 bg-ground/55 backdrop-blur-2xl">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-8">
        <div className="chrome font-display text-xl font-semibold">the spread model</div>
        <div className="flex items-center gap-2.5 font-mono text-[11px] tracking-[0.16em] text-muted">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-mint opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-mint shadow-[0_0_12px_var(--color-mint)]" />
          </span>
          LIVE &middot; COVERAGE ENGINE
        </div>
      </div>
    </header>
  );
}
