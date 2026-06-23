import { createSocialImageResponse } from "@/lib/social-image";
import { thihBrand } from "@/lib/thih-brand";

export const runtime = "edge";

export const alt = `${thihBrand.appName} - ${thihBrand.description}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return createSocialImageResponse();
}
