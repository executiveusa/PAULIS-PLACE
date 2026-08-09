import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata = {
  title: "Pauli's Place — Autonomous Business OS",
  description: "Speak the outcome. Pauli and the agents handle the work underneath.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#080807] text-stone-100">
        <div className="min-h-screen md:flex">
          <Sidebar />
          <main className="min-w-0 flex-1 md:ml-[248px]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
