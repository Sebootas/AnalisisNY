import React, { useState } from "react";
import "./App.css";

const PAGE_SIZE = 10;

function App() {
    const [businessFile, setBusinessFile] = useState(null);
    const [demoFile, setDemoFile] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [businessPage, setBusinessPage] = useState(1);
    const [demoPage, setDemoPage] = useState(1);
    const [businessData, setBusinessData] = useState([]);
    const [demoData, setDemoData] = useState([]);
    const [errorMessage, setErrorMessage] = useState("");

    const handleFileChange = (e, setter) => {
        setter(e.target.files[0]);
    };

    const handleAnalyze = async () => {
        setErrorMessage("");
        if (!businessFile || !demoFile) {
            setErrorMessage("Please upload both files.");
            return;
        }

        const formData = new FormData();
        formData.append("business", businessFile);
        formData.append("demographics", demoFile);

        try {
            const res = await fetch("http://localhost:5000/api/analyze", {
                method: "POST",
                body: formData,
            });

            const data = await res.json();

            if (data.status === "success") {
                setAnalysis(data.analysis);
                setBusinessData(data.analysis.business_data);
                setDemoData(data.analysis.demo_data);
                setBusinessPage(1);
                setDemoPage(1);
            } else {
                setErrorMessage(data.message || "Error in analysis.");
            }
        } catch (err) {
            console.error(err);
            setErrorMessage("Network error or server is unavailable.");
        }
    };

    function paginate(data, page, pageSize) {
        if (!Array.isArray(data)) return [];
        const start = (page - 1) * pageSize;
        return data.slice(start, start + pageSize);
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


    return (
        <div className="App">
            <h1>NYC Business & Demographics Analyzer</h1>

            {errorMessage && <div className="error-message">{errorMessage}</div>}

            <div>
                <input type="file" accept=".csv" onChange={(e) => handleFileChange(e, setBusinessFile)} />
                <label>Upload Businesses CSV</label>
            </div>

            <div>
                <input type="file" accept=".csv" onChange={(e) => handleFileChange(e, setDemoFile)} />
                <label>Upload Demographics CSV</label>
            </div>

            <button className="analyze-btn" onClick={handleAnalyze}>
                Analyze
            </button>

            {analysis && (
                <div className="results">
                    <h2>Results:</h2>
                    <p><strong>Total ZIPs analyzed:</strong> {analysis.total_zipcodes}</p>
                    <p><strong>Correlation with Median Income:</strong> {analysis.correlation_with_income ?? "Not available"}</p>
                    <h3>Top ZIPs with Most Businesses</h3>
                    <ul>
                        {analysis.top_zipcodes.map((zip, i) => (
                            <li key={i}>{zip.ZIP}: {zip.business_count} businesses</li>
                        ))}
                    </ul>

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
                    <table>
                        <thead>
                        <tr>
                            <th>ZIP</th>
                            <th>Gender (Male/Female)</th>
                            <th>Ethnicity</th>
                        </tr>
                        </thead>
                        <tbody>
                        {paginate(demoData, demoPage, PAGE_SIZE).map((demo, index) => (
                            <tr key={index}>
                                <td>{demo["ZIP"] ?? "-"}</td>
                                <td>{(demo["PERCENT MALE"] ?? "-") + " / " + (demo["PERCENT FEMALE"] ?? "-")}</td>
                                <td>{demo["PERCENT BLACK NON HISPANIC"] ?? "-"}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    {renderPagination(demoPage, demoData.length, setDemoPage)}
                </div>
            )}
        </div>
    );
}

export default App;
