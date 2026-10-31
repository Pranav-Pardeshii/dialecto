"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getActiveDemoUserId, setActiveDemoUserId } from "@/lib/api/client";
import { GraduationCap, Users, Check } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeUserId, setActiveUserId] = useState<number>(1);
  const [hydrated, setHydrated] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);

  useEffect(() => {
    setActiveUserId(getActiveDemoUserId());
    setHydrated(true);
  }, []);

  const handleSelectUser = (id: number) => {
    setActiveDemoUserId(id);
    setActiveUserId(id);
    setSwitcherOpen(false);
    queryClient.invalidateQueries();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("storage"));
    }
    if (id === 1) {
      router.push("/dashboard");
    } else {
      router.push("/class");
    }
  };

  const isTeacher = activeUserId === 2;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border-subtle bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative flex h-8 w-8 items-center justify-center transition group-hover:scale-105">
              <Image
                src="/logo.png"
                alt="Dialecto"
                width={32}
                height={32}
                className="object-contain"
                priority
              />
            </div>
            <div className="flex flex-col">
              <span className="font-serif text-base font-semibold tracking-tight text-ink-primary">
                Dialecto
              </span>
              <span className="text-[10px] tracking-wider uppercase text-ink-muted -mt-1 font-mono">
                Class 10 Biology
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 pl-4 border-l border-border-subtle">
            {!isTeacher ? (
              <>
                <Link
                  href="/dashboard"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/dashboard")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  Study Map
                </Link>
                <Link
                  href="/diagnostic"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/diagnostic")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  Diagnostic
                </Link>
                <Link
                  href="/practice"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/practice")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  Practice
                </Link>
                <Link
                  href="/review"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/review")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  Review
                </Link>
              </>
            ) : (
              <>
                <Link
                  href="/class"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/class")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  Class Heatmap & Insights
                </Link>
                <Link
                  href="/ops"
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    pathname.startsWith("/ops")
                      ? "bg-subtle text-ink-primary font-semibold"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-subtle/50"
                  }`}
                >
                  System Health
                </Link>
              </>
            )}
          </nav>
        </div>

        {/* Right side: Role Switcher */}
        <div className="relative">
          <button
            onClick={() => setSwitcherOpen(!switcherOpen)}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-border-subtle bg-surface text-xs text-ink-primary hover:bg-subtle transition shadow-subtle"
            aria-label="Switch User Role"
            aria-expanded={switcherOpen}
          >
            <div className="h-2 w-2 rounded-full bg-mastery-emerald animate-pulse" />
            <span className="font-medium">
              {hydrated ? (isTeacher ? "Ms. Rao" : "Aarav") : "Loading..."}
            </span>
            <span className="text-[11px] text-ink-muted">
              {hydrated ? (isTeacher ? "(Teacher)" : "(Student)") : ""}
            </span>
          </button>

          {/* Role Dropdown */}
          {switcherOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-lg border border-border-subtle bg-surface p-1.5 shadow-flyout z-50">
              <div className="px-2 py-1 text-[11px] font-medium text-ink-muted">
                Switch Role
              </div>
              <button
                onClick={() => handleSelectUser(1)}
                className={`flex w-full items-center justify-between rounded-md px-2.5 py-2 text-xs transition ${
                  activeUserId === 1
                    ? "bg-mastery-emeraldLight text-mastery-emeraldText font-semibold"
                    : "text-ink-primary hover:bg-subtle"
                }`}
              >
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-3.5 w-3.5" />
                  <div className="text-left">
                    <div>Aarav</div>
                    <div className="text-[10px] text-ink-muted">Class 10 Student</div>
                  </div>
                </div>
                {activeUserId === 1 && <Check className="h-3.5 w-3.5" />}
              </button>

              <button
                onClick={() => handleSelectUser(2)}
                className={`flex w-full items-center justify-between rounded-md px-2.5 py-2 text-xs transition ${
                  activeUserId === 2
                    ? "bg-mastery-emeraldLight text-mastery-emeraldText font-semibold"
                    : "text-ink-primary hover:bg-subtle"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5" />
                  <div className="text-left">
                    <div>Ms. Rao</div>
                    <div className="text-[10px] text-ink-muted">Biology Teacher</div>
                  </div>
                </div>
                {activeUserId === 2 && <Check className="h-3.5 w-3.5" />}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
