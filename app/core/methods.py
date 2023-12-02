import pandas as pd

def find_common(df1: pd.DataFrame, df2: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Finds the common rows between two dataframes by comparing the values of the specified columns.

    Args:
        df1 (pd.DataFrame): The first dataframe.
        df2 (pd.DataFrame): The second dataframe.
        cols (list[str]): The columns to compare.

    Returns:
        pd.DataFrame: The common rows between the two dataframes.
    """
    df1 = df1[cols]
    df2 = df2[cols]
    df = df1.merge(df2, on=cols, how='inner')
    return df

def find_missing(df1: pd.DataFrame, df2: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Finds the missing rows between two dataframes by comparing the values of the specified columns.

    Args:
        df1 (pd.DataFrame): The first dataframe.
        df2 (pd.DataFrame): The second dataframe.
        cols (list[str]): The columns to compare.

    Returns:
        pd.DataFrame: The missing rows between the two dataframes.
    """
    df1 = df1[cols]
    df2 = df2[cols]
    df = df1.merge(df2, on=cols, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
    return df

def find_new(df1: pd.DataFrame, df2: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Finds the new rows between two dataframes by comparing the values of the specified columns.

    Args:
        df1 (pd.DataFrame): The first dataframe.
        df2 (pd.DataFrame): The second dataframe.
        cols (list[str]): The columns to compare.

    Returns:
        pd.DataFrame: The new rows between the two dataframes.
    """
    df1 = df1[cols]
    df2 = df2[cols]
    df = df1.merge(df2, on=cols, how='outer', indicator=True).query('_merge == "right_only"').drop('_merge', axis=1)
    return df

# test the three functions

def test_find_common():
    df1 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df2 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df3 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7]})
    df4 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7], 'c': [8, 9, 10]})
    
    result1 = find_common(df1, df2, ['a', 'b'])
    print("Result 1:")
    print(result1)
    
    result2 = find_common(df1, df3, ['a', 'b'])
    print("Result 2:")
    print(result2)
    
    result3 = find_common(df1, df4, ['a', 'b'])
    print("Result 3:")
    print(result3)
    
    result4 = find_common(df3, df4, ['a', 'b'])
    print("Result 4:")
    print(result4)

def test_find_missing():
    df1 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df2 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df3 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7]})
    df4 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7], 'c': [8, 9, 10]})
    
    result1 = find_missing(df1, df2, ['a', 'b'])
    print("Result 1:")
    print(result1)
    
    result2 = find_missing(df1, df3, ['a', 'b'])
    print("Result 2:")
    print(result2)
    
    result3 = find_missing(df1, df4, ['a', 'b'])
    print("Result 3:")
    print(result3)
    
    result4 = find_missing(df3, df4, ['a', 'b'])
    print("Result 4:")
    print(result4.equals(df3))

def test_find_new():
    df1 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df2 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df3 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7]})
    df4 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 7], 'c': [8, 9, 10]})
    
    result1 = find_new(df1, df2, ['a', 'b'])
    print("Result 1:")
    print(result1.empty)
    
    result2 = find_new(df1, df3, ['a', 'b'])
    print("Result 2:")
    print(result2)
    
    result3 = find_new(df1, df4, ['a', 'b'])
    print("Result 3:")
    print(result3.equals(df4))
    
    result4 = find_new(df3, df4, ['a', 'b'])
    print("Result 4:")
    print(result4.empty)