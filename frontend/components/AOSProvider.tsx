"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";
import AOS from "aos";
import "aos/dist/aos.css";

export default function AOSProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  useEffect(() => {
    AOS.init({
      duration: 700,
      once: true,
      easing: "ease-in-out",
    });
  }, []);

  useEffect(() => {
    // AOS.init() only scans [data-aos] elements once, on first mount.
    // Without re-scanning after every client-side route change, elements
    // rendered post-navigation (e.g. after the redirect on logout) can be
    // left in an inconsistent/pre-animation layout state until a full
    // page reload forces AOS to recalculate everything from scratch.
    AOS.refreshHard();
  }, [pathname]);

  return <>{children}</>;
}
