import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata = {
  title: "Pauli's Place — Autonomous Business OS",
  description: "Voice-first mission control, persistent agents, governed execution, evidence, approvals, and Pauli's World.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#080808] text-stone-100 antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="min-w-0 flex-1 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
