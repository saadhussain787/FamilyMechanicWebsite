// eleventy.config.js
module.exports = function(eleventyConfig) {
    // Copy your physical shop image directly to the output folder
    eleventyConfig.addPassthroughCopy("frontend/shop-image.webp");

    return {
        // Force Eleventy to use Nunjucks to parse HTML files
        htmlTemplateEngine: "njk", 
        dir: {
            input: "frontend",
            output: "frontend/_site" // Where Eleventy will generate your compiled site
        }
    };
};