// aera-web/src/components/common/Loading.jsx
export default function Loading({ message = "Gathering atmospheric telemetry..." }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
      <div className="w-10 h-10 border-3 border-accent border-t-primary rounded-full animate-spin" />
      <p className="text-xs font-medium text-muted-foreground tracking-wide">{message}</p>
    </div>
  );
}