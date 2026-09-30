import api from "./api";

export const exportService = {
  async exportCsv(startDate: string, endDate: string): Promise<Blob> {
    const res = await api.post(
      "/export/csv",
      { start_date: startDate, end_date: endDate },
      { responseType: "blob" }
    );
    return res.data;
  },

  async exportCsvToS3(startDate: string, endDate: string): Promise<{ download_url: string }> {
    const res = await api.post("/export/csv/s3", {
      start_date: startDate,
      end_date: endDate,
    });
    return res.data;
  },

  // Helper: trigger browser download from blob
  downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};
