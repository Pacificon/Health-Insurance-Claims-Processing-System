import { ClaimsWorkspace } from "@/components/ClaimsWorkspace";
import { Providers } from "@/components/Providers";

export default function Home() {
  return (
    <Providers>
      <main className="min-h-screen bg-slate-100">
        <ClaimsWorkspace />
      </main>
    </Providers>
  );
}
