type ActionToastProps = {
  message: string | null;
};

export default function ActionToast({ message }: ActionToastProps) {
  if (!message) {
    return null;
  }

  return (
    <div className="fixed bottom-6 left-1/2 z-[1000] w-[min(360px,calc(100vw-32px))] -translate-x-1/2 rounded-full bg-slate-950 px-4 py-3 text-center text-sm font-semibold text-white shadow-soft">
      {message}
    </div>
  );
}
