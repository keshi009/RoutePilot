type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export default function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="rounded-[28px] border border-dashed border-slate-200 bg-white p-6 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-2xl">AI</div>
      <h2 className="mt-4 text-lg font-black text-slate-950">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
      {actionLabel && onAction ? (
        <button type="button" onClick={onAction} className="mt-5 rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white">
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
