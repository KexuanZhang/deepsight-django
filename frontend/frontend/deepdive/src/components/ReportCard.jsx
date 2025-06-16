import React from "react";

export default function ReportCard({ report }) {
  return (
    <div className="border rounded-lg overflow-hidden shadow">
      <img src={report.cover_image_url} alt="" className="w-full h-40 object-cover" />
      <div className="p-4">
        <h3 className="font-semibold mb-2">{report.report_title}</h3>
        <p className="text-gray-500 text-sm mb-2">By {report.author_name}</p>
        <p className="text-gray-700 line-clamp-3">{report.tldr || report.content}</p>
      </div>
    </div>
  );
}
