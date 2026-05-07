import { UrlForm } from "@/components/UrlForm";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-4 py-10">
      <div className="w-full rounded-xl border border-[#55524b] bg-[#2c2c29] p-6 shadow-2xl">
        <UrlForm />
      </div>
    </main>
  );
}
