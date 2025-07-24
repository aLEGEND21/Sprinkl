"use client";

import { BottomNavigation } from "@/components/bottom-navigation";
import { useSession, signIn } from "next-auth/react";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [userSynced, setUserSynced] = useState(false);
  const [syncError, setSyncError] = useState<null | string>(null);

  useEffect(() => {
    let cancelled = false;
    setUserSynced(false);
    setSyncError(null);
    if (status === "unauthenticated") {
      signIn("google", { callbackUrl: pathname });
    } else if (status === "authenticated") {
      // Notify the backend about the user login so that their account can be created if needed
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: session?.user?.id,
          email: session?.user?.email,
          name: session?.user?.name,
          image: session?.user?.image,
        }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Failed to sync user");
          return res.json();
        })
        .then(() => {
          if (!cancelled) setUserSynced(true);
        })
        .catch((err) => {
          if (!cancelled) {
            setSyncError(err.message || "Unknown error");
            setUserSynced(false);
            // Optionally, you could trigger a retry or show a message
            // For now, just log
            console.error("User sync error:", err);
          }
        });
    }
    return () => {
      cancelled = true;
    };
  }, [status, router, pathname]);

  return (
    <div>
      {/* pb-[73px] to account for height of bottom navigation */}
      <div className="pb-[73px]">
        {status === "authenticated" && userSynced ? (
          children
        ) : (
          // Loading spinner
          <div className="flex h-full w-full items-center justify-center py-40">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
            {syncError && <div className="ml-4 text-red-500">{syncError}</div>}
          </div>
        )}
      </div>
      <BottomNavigation />
    </div>
  );
}
