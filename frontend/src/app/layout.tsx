import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Green PM",
  description: "Engineering Project Intelligence — Evidence-backed progress and confidence for EPC projects",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        {/* Sidebar nav */}
        <div className="flex h-screen overflow-hidden">
          <nav className="w-56 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">
            <div className="px-4 py-5 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-gpm-green flex items-center justify-center">
                  <span className="text-white text-xs font-black">G</span>
                </div>
                <span className="text-white font-semibold text-sm">Green PM</span>
              </div>
              <p className="text-slate-500 text-xs mt-1.5">Northgate CCGT — Demo</p>
            </div>

            <div className="flex-1 px-2 py-4 space-y-1">
              <NavLink href="/" label="Dashboard" icon="▤" />
              <NavLink href="/reports" label="Weekly Report" icon="◧" />
            </div>

            <div className="px-4 py-3 border-t border-slate-800">
              <p className="text-slate-600 text-xs">Sourced from your schedule &amp; documents</p>
            </div>
          </nav>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, label, icon }: { href: string; label: string; icon: string }) {
  return (
    <a
      href={href}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400
                 hover:text-white hover:bg-slate-800 transition-colors text-sm"
    >
      <span className="text-slate-500 text-base">{icon}</span>
      {label}
    </a>
  );
}
