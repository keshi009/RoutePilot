import type { ReactNode } from "react";

type MobileShellProps = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
};

export default function MobileShell({ children, title, subtitle }: MobileShellProps) {
  return (
    <main className="min-h-screen bg-gradient-to-b from-[#eaf3ff] via-[#f8fbff] to-[#f4f7fb] px-4 py-5">
      <section className="mx-auto min-h-[calc(100vh-40px)] w-full max-w-[430px] overflow-hidden rounded-[34px] border border-white/80 bg-white shadow-soft">
        <div className="flex items-center justify-between bg-white/90 px-5 pb-3 pt-4">
          <div>
            <p className="text-[11px] font-semibold text-slate-400">RoutePilot</p>
            {title ? <h1 className="text-xl font-bold text-slate-950">{title}</h1> : null}
            {subtitle ? <p className="mt-1 text-xs text-slate-500">{subtitle}</p> : null}
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-xs font-bold text-white">
            AI
          </div>
        </div>
        {children}
      </section>
    </main>
  );
}
