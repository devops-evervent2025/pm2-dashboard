/**
 * Plain (non-client) branding config - shared between server components
 * (app/layout.tsx, for the favicon metadata) and client components
 * (InfraLinkLogo.tsx). Deliberately has NO "use client" directive:
 * exports from a "use client" file can only be safely used as React
 * components on the server side, not as plain constants/functions -
 * importing APP_NAME/getFaviconUrl from InfraLinkLogo.tsx directly into
 * the server-side layout caused a build-time "createProxy is not a
 * function" error. Splitting the plain data out here fixes that.
 */
export const BRANDING = {
  logoLight: process.env.NEXT_PUBLIC_LOGO_LIGHT_URL || "/branding/infralink-logo-light.png",
  logoDark: process.env.NEXT_PUBLIC_LOGO_DARK_URL || "/branding/infralink-logo-dark.png",
  iconLight: process.env.NEXT_PUBLIC_ICON_LIGHT_URL || "/branding/infralink-icon-light.png",
  iconDark: process.env.NEXT_PUBLIC_ICON_DARK_URL || "/branding/infralink-icon-dark.png",
  favicon: process.env.NEXT_PUBLIC_FAVICON_URL || "/branding/infralink-favicon.png",
};

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "InfraLink";

export function getFaviconUrl(): string {
  return BRANDING.favicon;
}
