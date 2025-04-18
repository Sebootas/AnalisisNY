import React, { useState } from "react";
import Papa from "papaparse";
import "./App.css";

const PAGE_SIZE = 10;

function App() {
    const [businessFile, setBusinessFile] = useState(null);
    const [demoFile, setDemoFile] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [businessPage, setBusinessPage] = useState(1);
    const [demoPage, setDemoPage] = useState(1);
    const [zipIndustryPage, setZipIndustryPage] = useState(1);
    const [individualZipPage, setIndividualZipPage] = useState(1);
    const [businessData, setBusinessData] = useState([]);
    const [demoData, setDemoData] = useState([]);
    const [zipIndustryData, setZipIndustryData] = useState([]);
    const [individualZipData, setIndividualZipData] = useState([]);
    const [errorMessage, setErrorMessage] = useState("");
    const [businessPreview, setBusinessPreview] = useState([]);
    const [demoPreview, setDemoPreview] = useState([]);
    const [loading, setLoading] = useState(false);

    // Función de renderización para las vistas previas de la tabla
    function renderTablePreview(data) {
        if (!data || data.length === 0) return null;
        const headers = Object.keys(data[0]);

        return (
            <table>
                <thead>
                <tr>
                    {headers.map((header, index) => (
                        <th key={index}>{header}</th>
                    ))}
                </tr>
                </thead>
                <tbody>
                {data.map((row, index) => (
                    <tr key={index}>
                        {headers.map((header, index) => (
                            <td key={index}>{row[header] ?? '-'}</td>
                        ))}
                    </tr>
                ))}
                </tbody>
            </table>
        );
    }

    const handleFileChange = (e, setter, setPreview) => {
        const file = e.target.files[0];
        setter(file);

        // Leer el archivo CSV para mostrar vista previa
        Papa.parse(file, {
            complete: (result) => {
                setPreview(result.data.slice(0, 5)); // Mostrar las primeras 5 filas
            },
            header: true,
        });
    };

    const handleDrop = (e) => {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length) {
            handleFileChange({ target: { files } }, setBusinessFile); // Puedes usarlo para los dos inputs
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const handleAnalyze = async () => {
        setErrorMessage("");
        setLoading(true); // Start loading

        if (!businessFile || !demoFile) {
            setErrorMessage("Please upload both files.");
            setLoading(false); // Stop loading
            return;
        }

        const tryAnalyze = async (bizFile, demoFile) => {
            const formData = new FormData();
            formData.append("business", bizFile);
            formData.append("demographics", demoFile);

            const res = await fetch("http://localhost:5000/api/analyze", {
                method: "POST",
                body: formData,
            });

            return await res.json();
        };

        try {
            let data = await tryAnalyze(businessFile, demoFile);

            if (data.status === "success") {
                setAnalysis(data.analysis);
                setBusinessData(data.analysis.business_data);
                setDemoData(data.analysis.demo_data);
                setZipIndustryData(data.analysis.grouped_by_zip_industry);
                setIndividualZipData(data.analysis.top_individual_zipcodes);
                setBusinessPage(1);
                setDemoPage(1);
                setZipIndustryPage(1);
                setIndividualZipPage(1);
            } else {
                const switched = data?.error?.toLowerCase().includes("no se encontró una columna zip válida");

                if (switched) {
                    // Intenta con los archivos intercambiados
                    const retryData = await tryAnalyze(demoFile, businessFile);
                    if (retryData.status === "success") {
                        setAnalysis(retryData.analysis);
                        setBusinessData(retryData.analysis.business_data);
                        setDemoData(retryData.analysis.demo_data);
                        setZipIndustryData(retryData.analysis.grouped_by_zip_industry);
                        setIndividualZipData(retryData.analysis.top_individual_zipcodes);
                        setBusinessPage(1);
                        setDemoPage(1);
                        setZipIndustryPage(1);
                        setIndividualZipPage(1);
                    } else {
                        setErrorMessage("Error al analizar incluso tras intercambiar archivos: " + (retryData.message || retryData.error));
                    }
                } else {
                    setErrorMessage(data.message || "Error in analysis.");
                }
            }
        } catch (err) {
            console.error(err);
            setErrorMessage("Network error or server is unavailable.");
        } finally {
            setLoading(false); // Stop loading in all cases
        }
    };


    function paginate(data, page, pageSize) {
        if (!Array.isArray(data)) return [];
        const start = (page - 1) * pageSize;
        return data.slice(start + 0, start + pageSize);
    }

    function renderPagination(currentPage, totalItems, setPage) {
        const totalPages = Math.ceil(totalItems / PAGE_SIZE);
        const pageBlockSize = 10;
        const currentBlock = Math.floor((currentPage - 1) / pageBlockSize);
        const blockStart = currentBlock * pageBlockSize + 1;
        const blockEnd = Math.min(blockStart + pageBlockSize - 1, totalPages);

        const pages = [];
        for (let i = blockStart; i <= blockEnd; i++) {
            pages.push(
                <button
                    key={i}
                    onClick={() => setPage(i)}
                    className={currentPage === i ? "active-page" : ""}
                >
                    {i}
                </button>
            );
        }
        return (
            <div className="pagination">
                <button
                    onClick={() => setPage(Math.max(1, blockStart - 1))}
                    disabled={blockStart === 1}
                >
                    Previous
                </button>
                {pages}
                <button
                    onClick={() => setPage(Math.min(totalPages, blockEnd + 1))}
                    disabled={blockEnd >= totalPages}
                >
                    Next
                </button>
            </div>
        );
    }

    const ETHNICITY_COLUMNS = [
        "PERCENT PACIFIC ISLANDER",
        "PERCENT HISPANIC LATINO",
        "PERCENT AMERICAN INDIAN",
        "PERCENT ASIAN NON HISPANIC",
        "PERCENT WHITE NON HISPANIC",
        "PERCENT BLACK NON HISPANIC",
        "PERCENT OTHER ETHNICITY",
        "PERCENT ETHNICITY UNKNOWN"
    ];

    return (
        <div className="App">
            <h1>NYC Business & Demographics Analyzer</h1>

            {errorMessage && <div className="error-message">{errorMessage}</div>}

            <div className="upload-section">
                <h2>📂 Upload CSV Files</h2>

                <div className="file-input-wrapper">
                    <div className="file-drop-area" onDrop={(e) => handleFileChange(e, setBusinessFile, setBusinessPreview)} onDragOver={(e) => e.preventDefault()}>
                        <p>Drag & drop your Business file here or</p>
                        <label className="custom-file-input">
                            Choose Files
                            <input
                                type="file"
                                accept=".csv"
                                onChange={(e) => handleFileChange(e, setBusinessFile, setBusinessPreview)}
                                className="file-input"
                            />
                        </label>
                    </div>
                    {businessFile && <span className="filename">{businessFile.name}</span>}
                </div>

                <div className="file-input-wrapper">
                    <div className="file-drop-area" onDrop={(e) => handleFileChange(e, setDemoFile, setDemoPreview)} onDragOver={(e) => e.preventDefault()}>
                        <p>Drag & drop your Demographic file here or</p>
                        <label className="custom-file-input">
                            Choose Files
                            <input
                                type="file"
                                accept=".csv"
                                onChange={(e) => handleFileChange(e, setDemoFile, setDemoPreview)}
                                className="file-input"
                            />
                        </label>
                    </div>
                    {demoFile && <span className="filename">{demoFile.name}</span>}
                </div>

                <button className="analyze-btn" onClick={handleAnalyze}>
                    🚀 Analyze Data
                </button>
            </div>

            {loading && (
                <div className="loader"></div>
            )}

            {analysis && (
                <div className="results">
                    <h2>Results:</h2>
                    <p><strong>Total ZIPs analyzed:</strong> {analysis.total_zipcodes}</p>

                    <h3>Top ZIPs with Most Businesses</h3>
                    <ul>
                        {analysis.top_zipcodes.map((zip, i) => (
                            <li key={i}>{zip.ZIP}: {zip.business_count} businesses</li>
                        ))}
                    </ul>

                    <h3>Top ZIPs with Most Individuals (Solo nombres tipo persona)</h3>
                    <table>
                        <thead>
                        <tr>
                            <th>ZIP</th>
                            <th>Individual Count</th>
                        </tr>
                        </thead>
                        <tbody>
                        {paginate(individualZipData, individualZipPage, PAGE_SIZE).map((zip, i) => (
                            <tr key={i}>
                                <td>{zip.ZIP}</td>
                                <td>{zip.individual_count}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    {renderPagination(individualZipPage, individualZipData.length, setIndividualZipPage)}

                    <h3>Negocios agrupados por ZIP e Industria</h3>
                    <table>
                        <thead>
                        <tr>
                            <th>ZIP</th>
                            <th>Industry</th>
                            <th>Count</th>
                        </tr>
                        </thead>
                        <tbody>
                        {paginate(zipIndustryData, zipIndustryPage, PAGE_SIZE).map((item, i) => (
                            <tr key={i}>
                                <td>{item.ZIP}</td>
                                <td>{item.Industry}</td>
                                <td>{item.count_by_zip_industry}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>

                    {renderPagination(zipIndustryPage, zipIndustryData.length, setZipIndustryPage)}

                    <h3>Business Data</h3>
                    <table>
                        <thead>
                        <tr>
                            <th>Business Name</th>
                            <th>Industry</th>
                            <th>ZIP</th>
                            <th>Address</th>
                        </tr>
                        </thead>
                        <tbody>
                        {paginate(businessData, businessPage, PAGE_SIZE).map((business, index) => (
                            <tr key={index}>
                                <td>{business["Business Name"] ?? "-"}</td>
                                <td>{business["Industry"] ?? "-"}</td>
                                <td>{business["ZIP"] ?? "-"}</td>
                                <td>{(business["Address Building"] ?? "") + " " + (business["Address Street Name"] ?? "")}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    {renderPagination(businessPage, businessData.length, setBusinessPage)}

                    <h3>Demographic Data</h3>
                    <div className="table-scroll">
                        <table>
                            <thead>
                            <tr>
                                <th>ZIP</th>
                                <th>Gender (Male/Female)</th>
                                {ETHNICITY_COLUMNS.map(col => (
                                    <th key={col}>{col}</th>
                                ))}
                            </tr>
                            </thead>
                            <tbody>
                            {paginate(demoData, demoPage, PAGE_SIZE).map((demo, index) => (
                                <tr key={index}>
                                    <td>{demo["ZIP"] ?? "-"}</td>
                                    <td>{(demo["PERCENT MALE"] ?? "-") + " / " + (demo["PERCENT FEMALE"] ?? "-")}</td>
                                    {ETHNICITY_COLUMNS.map(col => (
                                        <td key={col}>{demo[col] ?? "-"}</td>
                                    ))}
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                    {renderPagination(demoPage, demoData.length, setDemoPage)}
                </div>
            )}
        </div>
    );
}

export default App;
