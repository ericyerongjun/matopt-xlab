/**
 * FileUploader — drag-and-drop file upload using react-dropzone.
 * Accepts common student document and source file formats.
 */

import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface Props {
    onFile: (file: File) => void;
    accept?: Record<string, string[]>;
    disabled?: boolean;
}

const DEFAULT_ACCEPT: Record<string, string[]> = {
    "application/pdf": [".pdf"],
    "application/vnd.ms-powerpoint": [".ppt"],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".r", ".rmd", ".py", ".c", ".cpp", ".java"],
    "application/json": [".ipynb"],
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/heic": [".heic"],
};

export default function FileUploader({
    onFile,
    accept = DEFAULT_ACCEPT,
    disabled = false,
}: Props) {
    const onDrop = useCallback(
        (accepted: File[]) => {
            if (accepted.length > 0) onFile(accepted[0]);
        },
        [onFile]
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept,
        maxFiles: 1,
        disabled,
    });

    return (
        <div
            {...getRootProps()}
            className={`file-uploader ${isDragActive ? "file-uploader--active" : ""}`}
        >
            <input {...getInputProps()} />
            {isDragActive ? (
                <p>Drop the file here…</p>
            ) : (
                <p>Drop PDF, Office, code, notebook, or image files</p>
            )}
        </div>
    );
}
