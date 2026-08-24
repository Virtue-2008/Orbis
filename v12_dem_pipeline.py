import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import sobel

def create_sample_dem(filename="sample_terrain.tif"):
    print("🏔️ Generating sample 30m terrain elevation data...")
    x = np.linspace(-5, 5, 100)
    y = np.linspace(-5, 5, 100)
    X, Y = np.meshgrid(x, y)
    
    # Mathematical mountain: 1000m base + a Gaussian peak
    elevation = 1000 + 500 * np.exp(-(X**2 + Y**2) / 4.0)
    
    # Save as a GeoTIFF using rasterio
    transform = from_origin(10.0, 50.0, 0.00027, 0.00027) # ~30m resolution
    
    with rasterio.open(
        filename, 'w', driver='GTiff',
        height=elevation.shape[0], width=elevation.shape[1],
        count=1, dtype=elevation.dtype,
        crs='+proj=latlong', transform=transform,
    ) as dst:
        dst.write(elevation, 1)
        
    print(f"✅ Saved DEM to {filename}")
    return filename

def process_topography(dem_path):
    print("🛰️ Loading DEM and calculating Slope & Aspect matrices...")
    
    with rasterio.open(dem_path) as src:
        elevation = src.read(1)
        cell_size = 30.0 
        
        # Calculate gradients (rate of change) in X and Y directions using Sobel
        dz_dx = sobel(elevation, axis=1) / (8.0 * cell_size)
        dz_dy = sobel(elevation, axis=0) / (8.0 * cell_size)
        
        # Slope: The steepness (in degrees)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = np.degrees(slope_rad)
        
        # Aspect: The compass direction the slope faces (0-360)
        aspect_rad = np.arctan2(dz_dy, -dz_dx)
        aspect_deg_raw = np.degrees(aspect_rad)
        aspect_deg = (90.0 - aspect_deg_raw) % 360.0
        
        print("\n📊 Terrain Analysis Complete!")
        print(f"Max Elevation: {elevation.max():.1f} m")
        print(f"Max Steepness: {slope_deg.max():.1f} degrees")
        print(f"Aspect Range:  {aspect_deg.min():.1f} to {aspect_deg.max():.1f} degrees")
        
        return elevation, slope_deg, aspect_deg

if __name__ == "__main__":
    dem_file = create_sample_dem()
    elevation, slope, aspect = process_topography(dem_file)