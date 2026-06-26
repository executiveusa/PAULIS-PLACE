import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata = {
  title: 'DigiFactory - Autonomous Digital Products',
  description: 'AI-powered digital product factory',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white min-h-screen">
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
