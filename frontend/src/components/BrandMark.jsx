function BrandMark({ className = "" }) {
    return (
        <svg
            className={`brand-mark ${className}`.trim()}
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
            focusable="false"
        >
            <path
                d="M3.5 7.5 9 24.5 16 11.5 23 24.5 28.5 7.5"
                stroke="currentColor"
                strokeWidth="3.2"
                strokeLinecap="square"
                strokeLinejoin="miter"
            />
        </svg>
    );
}

export default BrandMark;
