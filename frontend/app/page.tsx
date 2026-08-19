"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { PageLoader } from "@/components/Preloader";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getToken() ? "/dashboard" : "/login");
  }, [router]);

  return <PageLoader message="Loading InfraLink" />;
}
