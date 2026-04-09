import { proxyBinaryDownload } from "@/lib/download-proxy";

type CompanyExcelRouteProps = {
  params: Promise<{ cd_cvm: string }>;
};

export async function GET(_: Request, { params }: CompanyExcelRouteProps) {
  const { cd_cvm } = await params;
  return proxyBinaryDownload(`/companies/${cd_cvm}/export/excel`);
}
